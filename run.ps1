# GraphBees local launcher (Windows PowerShell)
# ---------------------------------------------
# What this script does:
#   1) Ensures Python is available
#   2) Creates a virtual environment if needed
#   3) Installs project dependencies
#   4) Shows every .env variable for edit (Enter keeps current)
#   5) Launches the app

# Stop immediately on errors.
$ErrorActionPreference = "Stop"

# Always run from the repository root (the folder this script lives in).
Set-Location -Path $PSScriptRoot

# Choose a Python command. Require Python 3.10+ and prefer newer versions first.
$pythonCmd = $null
$pythonVenvArgs = @("-m", "venv", "venv")
if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($candidate in @("-3.12", "-3.11", "-3.10")) {
        try {
            & py $candidate --version *> $null
            if ($LASTEXITCODE -eq 0) {
                $pythonCmd = "py"
                $pythonVenvArgs = @($candidate, "-m", "venv", "venv")
                break
            }
        } catch {
            continue
        }
    }
}

if ($null -eq $pythonCmd -and (Get-Command python -ErrorAction SilentlyContinue)) {
    try {
        & python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = "python"
        }
    } catch {
    }
}

if ($null -eq $pythonCmd) {
    Write-Host "Python 3.10+ is required. Please install Python 3.10, 3.11, or 3.12 and try again." -ForegroundColor Red
    exit 1
}

# Recreate virtual environment if it exists but uses Python < 3.10.
if (Test-Path ".\venv\Scripts\python.exe") {
    try {
        & .\venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Recreating virtual environment with Python 3.10+ (existing venv is older)..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force venv
        }
    } catch {
        Write-Host "Recreating virtual environment (existing venv is invalid)..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force venv
    }
}

# Create virtual environment once; reuse it on future runs.
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    & $pythonCmd @pythonVenvArgs
}

# Activate virtual environment for this PowerShell session.
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# Install/refresh dependencies.
Write-Host "Installing dependencies..." -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -r requirements.txt

# Create .env template if it does not exist.
if (-not (Test-Path ".env")) {
    "LLM_API=`nLLM_URL=`nMODEL=`nGRAPHBEES_ALLOW_SHUTDOWN=1" | Set-Content -Path ".env" -Encoding UTF8
}

# Read existing values from .env (last occurrence wins).
$lines = Get-Content ".env"

function Get-EnvValue {
    param([string]$Key, [string[]]$Content)

    $match = ($Content | Where-Object { $_ -match "^$Key=" } | Select-Object -Last 1)
    if ($null -eq $match) {
        return ""
    }
    return ($match -replace "^$Key=", "")
}

# Build key list from existing .env lines (in file order, deduplicated).
$keys = [System.Collections.Generic.List[string]]::new()
foreach ($line in $lines) {
    if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=') {
        $key = $Matches[1]
        if ($key -eq "PYTHON_JULIACALL_THREADS") {
            continue
        }
        if (-not $keys.Contains($key)) {
            $null = $keys.Add($key)
        }
    }
}

# Ensure required keys are always present in the prompt flow.
foreach ($requiredKey in @("LLM_API", "LLM_URL", "MODEL")) {
    if (-not $keys.Contains($requiredKey)) {
        $null = $keys.Add($requiredKey)
    }
}

$values = @{}

Write-Host "Configure .env values (press Enter to keep current value)" -ForegroundColor Cyan
foreach ($key in $keys) {
    if ($key -eq "GRAPHBEES_ALLOW_SHUTDOWN") {
        continue
    }
    $currentValue = Get-EnvValue -Key $key -Content $lines
    $inputValue = Read-Host "$key [current: $currentValue]"
    if ([string]::IsNullOrWhiteSpace($inputValue)) {
        $inputValue = $currentValue
    }
    $values[$key] = $inputValue
}

# Always force shutdown flag default.
$values["GRAPHBEES_ALLOW_SHUTDOWN"] = "1"
if (-not $keys.Contains("GRAPHBEES_ALLOW_SHUTDOWN")) {
    $null = $keys.Add("GRAPHBEES_ALLOW_SHUTDOWN")
}

# Validate required values.
if ([string]::IsNullOrWhiteSpace($values["LLM_API"])) {
    Write-Host "LLM_API is required." -ForegroundColor Red
    exit 1
}
if ([string]::IsNullOrWhiteSpace($values["LLM_URL"])) {
    Write-Host "LLM_URL is required." -ForegroundColor Red
    exit 1
}
if ([string]::IsNullOrWhiteSpace($values["MODEL"])) {
    Write-Host "MODEL is required." -ForegroundColor Red
    exit 1
}

# Rewrite .env using prompted values.
$output = [System.Collections.Generic.List[string]]::new()
$null = $output.Add("  ")
foreach ($key in $keys) {
    $null = $output.Add("$key=$($values[$key])")
}
$output | Set-Content -Path ".env" -Encoding UTF8

Write-Host "Using LLM_URL=$($values["LLM_URL"])" -ForegroundColor Green
Write-Host "Using MODEL=$($values["MODEL"])" -ForegroundColor Green

# Start Streamlit through the package entrypoint.
Write-Host "Starting GraphBees..." -ForegroundColor Green
python -m app
