# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GraphBees is a Python agentic app for network/graph mining and combinatorial optimization. It uses DeepSeek's API (OpenAI-compatible) to let an LLM agent invoke algorithms implemented in Julia via the [JuliAlg](https://github.com/hoavu-cs/JuliAlg) package. The web UI is built with Streamlit (Python-only chat interface with built-in markdown and Plotly support).

## Commands

```bash
pip install -r requirements.txt   # install dependencies (openai, python-dotenv, juliacall, streamlit)
python -m app                     # run the Streamlit app on http://127.0.0.1:8080
# or: streamlit run app/main.py --server.port=8080
```

Requires `LLM_API` and `LLM_URL` in `.env` (loaded via python-dotenv), plus a local clone of JuliAlg at the repo root (`./JuliAlg/`).

## Architecture

The app follows a four-layer design:

1. **`app/main.py`** — Streamlit app. Uses `st.chat_message` and `st.chat_input` for the chat UI. Julia is initialized once via `@st.cache_resource`. Chat history is persisted in `st.session_state.messages`. Tool cards are rendered with styled HTML and `st.expander`. Charts use `st.plotly_chart` with Plotly figures. **`app/__main__.py`** provides the `python -m app` entry point.

2. **`app/agent.py`** — Agentic loop. Sends user messages to DeepSeek (via OpenAI SDK) with function-calling tools, dispatches any tool calls, feeds results back, and repeats until a final text response. Returns `{"answer": str, "tool_logs": [...]}` with solver metadata (algorithm, guarantee, complexity, timing) per tool call.

3. **`app/tools/network_tools.py`** — Defines tool schemas (OpenAI function-calling JSON format), `TOOL_META` (algorithm/guarantee/complexity metadata per tool), and a `dispatch()` router that maps tool names to Julia bridge functions. The dispatch layer converts LLM JSON arguments (e.g. edges as nested arrays, weight keys as `"u,v"` strings) into Python types (tuples, dicts) before calling the bridge.

4. **`app/julia_bridge/runner.py`** — Python-to-Julia bridge via `juliacall`. Sets `JULIA_PROJECT` to `JuliAlgEnv/` before importing juliacall. Each function builds a Julia code string with f-strings, executes it via `jl.seval()`, and converts results back to Python types. `init_julialg()` must be called once at startup to load JuliAlg and Graphs packages.

**Frontend:** Defined entirely in `app/main.py` using Streamlit components — `st.chat_message` bubbles, tool execution cards (indigo/red accent borders), Plotly charts for knapsack/interval visualizations, and native markdown rendering.

Data flow: `main.py (Streamlit)` → `agent.py (loop)` → `network_tools.py (dispatch)` → `runner.py (juliacall)` → JuliAlg (Julia)

## Available Tools (10 total)

**Graph/network:** `influence_maximization`, `densest_subgraph`, `k_core_decomposition`, `betweenness_centrality`, `pagerank`

**Combinatorial optimization:** `ptas_knapsack`, `bin_packing`, `weighted_interval_scheduling`, `set_cover`, `max_coverage`

Always use `ptas_knapsack` for knapsack problems (never `exact_knapsack`).

## Key Conventions

- Edge lists are `list[tuple[int, int]]` in Python, built into Julia `SimpleGraph`/`SimpleDiGraph` via code generation in `runner.py`.
- Edge weights use `Dict{Tuple{Int,Int}, Float64}` on the Julia side; Python side uses `dict[tuple[int,int], float]`.
- Tool schemas in `network_tools.py` must stay in sync with the bridge functions in `runner.py`. When adding a new tool, update three things: `TOOL_META`, `TOOLS` schema list, and the `dispatch()` if-chain — plus the corresponding function in `runner.py`.
- All bridge functions return JSON-serializable Python dicts/lists (not raw Julia objects).
- The Julia environment is set via `JULIA_PROJECT` in `runner.py` pointing to `JuliAlgEnv/` at the repo root.
