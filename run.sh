#!/usr/bin/env bash

# GraphBees local launcher (macOS/Linux)
# --------------------------------------
# What this script does:
#   1) Ensures Python is available
#   2) Creates a virtual environment if needed
#   3) Installs project dependencies
#   4) Shows every .env variable for edit (Enter keeps current)
#   5) Launches the app

# Exit on error, undefined variable, or failed pipeline command.
set -euo pipefail

# Always run from the repository root (the folder this script lives in).
cd "$(dirname "$0")"

# Pick a Python executable. Require Python 3.10+ and prefer newer versions first.
if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN="python3.12"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="python3.11"
elif command -v python3.10 >/dev/null 2>&1; then
  PYTHON_BIN="python3.10"
else
  echo "❌ Python 3.10+ is required. Please install Python 3.10, 3.11, or 3.12 and try again."
  exit 1
fi

# Recreate virtual environment if it exists but uses Python < 3.10.
if [[ -d "venv" ]]; then
  if ! venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "♻️ Recreating virtual environment with $PYTHON_BIN (existing venv is older than Python 3.10)..."
    rm -rf venv
  fi
fi

# Create virtual environment once; reuse it on future runs.
if [[ ! -d "venv" ]]; then
  echo "📦 Creating virtual environment with $PYTHON_BIN..."
  "$PYTHON_BIN" -m venv venv
fi

# Activate the virtual environment for this shell session.
echo "🔌 Activating virtual environment..."
# shellcheck source=/dev/null
source venv/bin/activate

# Install/refresh dependencies.
echo "⬆️  Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# Create .env template if it does not exist.
if [[ ! -f ".env" ]]; then
  cat > .env <<'EOF'
LLM_API=
LLM_URL=
MODEL=
GRAPHBEES_ALLOW_SHUTDOWN=1
EOF
fi

get_env_value() {
  local key="$1"
  grep -E "^${key}=" .env | tail -n 1 | cut -d '=' -f2- || true
}

contains_key() {
  local needle="$1"
  shift
  for item in "$@"; do
    if [[ "$item" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}

# Build key list from existing .env lines (in file order, deduplicated).
ENV_KEYS=()
while IFS= read -r key; do
  if [[ "$key" == "PYTHON_JULIACALL_THREADS" ]]; then
    continue
  fi
  ENV_KEYS+=("$key")
done < <(awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/{ if(!seen[$1]++) print $1 }' .env)

# Ensure required keys are always present in the prompt flow.
for required_key in LLM_API LLM_URL MODEL; do
  if ! contains_key "$required_key" "${ENV_KEYS[@]}"; then
    ENV_KEYS+=("$required_key")
  fi
done

set_prompt_value() {
  local key="$1"
  local value="$2"
  printf -v "ENVVAL_${key}" '%s' "$value"
}

get_prompt_value() {
  local key="$1"
  local var_name="ENVVAL_${key}"
  printf '%s' "${!var_name-}"
}

mask_secret_tail4() {
  local value="$1"
  if [[ -z "$value" ]]; then
    printf '%s' ""
    return
  fi
  local tail="${value: -4}"
  printf '%s' "***${tail}"
}

echo
echo "🛠️  Configure .env values (press Enter to keep current value)"
for key in "${ENV_KEYS[@]}"; do
  if [[ "$key" == "GRAPHBEES_ALLOW_SHUTDOWN" ]]; then
    continue
  fi
  current_value="$(get_env_value "$key")"
  display_value="$current_value"
  if [[ "$key" == "LLM_API" ]]; then
    display_value="$(mask_secret_tail4 "$current_value")"
  fi
  read -r -p "${key} [current: ${display_value}]: " user_value
  if [[ -z "$user_value" ]]; then
    user_value="$current_value"
  fi
  set_prompt_value "$key" "$user_value"
done

# Always force shutdown flag default.
set_prompt_value "GRAPHBEES_ALLOW_SHUTDOWN" "1"
if ! contains_key "GRAPHBEES_ALLOW_SHUTDOWN" "${ENV_KEYS[@]}"; then
  ENV_KEYS+=("GRAPHBEES_ALLOW_SHUTDOWN")
fi

# Validate required values.
if [[ -z "$(get_prompt_value "LLM_API")" ]]; then
  echo "❌ LLM_API is required."
  exit 1
fi
if [[ -z "$(get_prompt_value "LLM_URL")" ]]; then
  echo "❌ LLM_URL is required."
  exit 1
fi
if [[ -z "$(get_prompt_value "MODEL")" ]]; then
  echo "❌ MODEL is required."
  exit 1
fi

# Rewrite .env using prompted values.
{
  for key in "${ENV_KEYS[@]}"; do
    printf '%s=%s\n' "$key" "$(get_prompt_value "$key")"
  done
} > .env

echo
echo "✅ Using LLM_URL=$(get_prompt_value "LLM_URL")"
echo "✅ Using MODEL=$(get_prompt_value "MODEL")"

# Start Streamlit through the package entrypoint.
echo "🚀 Starting GraphBees..."
python -m app
