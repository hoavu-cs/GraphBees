# GraphBees

GraphBees is a Streamlit Python app for solving combinatorial optimization problems from natural-language prompts.
It uses an LLM to extract the underlying optimization problem from your prompt and then applies an algorithmic solver to compute the solution. This approach guarantees correctness rather than relying on LLM guesswork.

```text
Query => LLM => Algorithmic Solvers => Answer => LLM => Output.
```

## Features

- Natural-language optimization workflow
- Tool-backed solvers (knapsack, bin packing, interval scheduling, set cover, max coverage, bipartite matching, mixed ILP,...)
- Interactive visual summaries in the chat UI for some problems
- Tutorials page with example problem formulations

## Requirements

- Python 3.10+
- Julia (managed automatically through `juliacall` when needed)
- API configuration:
   - `LLM_API`
   - `LLM_URL`
   - `MODEL`

## Webapp

The app is hosted at [https://www.graphbees.xyz/](https://www.graphbees.xyz/).

## Running Locally

Use the provided launcher scripts (recommended). 

## Quick Start (Scripts)

### macOS / Linux

```bash
git clone https://github.com/hoavu-cs/GraphBees.git
cd GraphBees
./run.sh
```

Enter LLM API, LLM URL, and MODEL (press Enter to keep current value if existed)
It would look like this
```
🛠️  Configure .env values (press Enter to keep current value)
LLM_API [current: sk-8...]: 
LLM_URL [current: https://api.deepseek.com]: 
MODEL [current: deepseek-chat]: 
```

or 

```
LLM_API=sk-8...
LLM_URL=https://api.openai.com/v1
MODEL=gpt-4.1-mini
```

### Windows (PowerShell)

```powershell
git clone https://github.com/hoavu-cs/GraphBees.git
cd GraphBees
.\run.ps1
```

Enter LLM API, LLM URL, and MODEL (press Enter to keep current value)

### Local LLM with Ollama

Few local LLMs are reliable enough with tool-calling. If you want to use a local LLM with Ollama, first set up your model in Ollama, then configure `.env` like this.

```
LLM_API=ollama
LLM_URL=http://127.0.0.1:11434/v1
MODEL=MFDoom/deepseek-r1-tool-calling:7b
GRAPHBEES_ALLOW_SHUTDOWN=1
```

If PowerShell blocks scripts, run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Quick Start (Manual)

### macOS / Linux

```bash
git clone https://github.com/hoavu-cs/GraphBees.git
cd GraphBees
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app
```

### Windows (PowerShell)

```powershell
git clone https://github.com/hoavu-cs/GraphBees.git
cd GraphBees
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app
```

Open: `http://127.0.0.1:8501` (or configured port).

## Configuration

The launcher scripts create/update `.env` automatically. If you configure manually, use:

```dotenv
LLM_API=...
LLM_URL=... # required (e.g., https://api.deepseek.com)
MODEL=...   # required (e.g., deepseek-chat)
GRAPHBEES_ALLOW_SHUTDOWN=1
```

### Ollama example

```dotenv
LLM_API=ollama
LLM_URL=http://127.0.0.1:11434/v1
MODEL=MFDoom/deepseek-r1-tool-calling:7b
GRAPHBEES_ALLOW_SHUTDOWN=1
```

Julia thread mode is always set to `auto` by the app runtime.

## Project Structure

```text
app/
   agent.py                # LLM tool-calling loop
   main.py                 # Streamlit chat UI
   julia_bridge/runner.py  # Python <-> Julia bridge
   tools/network_tools.py  # Tool schemas + dispatch
   pages/                  # Additional Streamlit pages
```

## License

MIT
