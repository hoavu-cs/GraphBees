"""
Agentic loop: sends messages to DeepSeek, handles tool calls, returns final answer.
"""

import json
import time

from dotenv import load_dotenv
from openai import OpenAI

from app.config import resolve_api_config
from app.julia_bridge.runner import julia_nthreads
from app.tools.network_tools import TOOL_META, TOOLS, dispatch

load_dotenv()

SYSTEM_PROMPT = """You are a combinatorial optimization assistant. Users will describe \
real-world optimization problems in natural language. Your job is to:

1. **Detect** which optimization problem the description maps to.
2. **Extract** the structured parameters from the natural language input.
3. **Call** the appropriate tool with the extracted parameters.
4. **Explain** the solution in plain language, referring back to the user's original context.  

## Available problem types

### Combinatorial optimization
- **0/1 Knapsack** — "I have a budget/capacity of X, and items with costs and values/utilities." \
Always use ptas_knapsack.
- **Bin packing** — "I need to pack items of various sizes into containers of fixed capacity."
- **Weighted interval scheduling** — "I have jobs/events with start times, end times, and values; \
which non-overlapping set maximizes value?"https://github.com/anthropics/claude-code/issues/617
- **Set cover** — "I need to cover all elements using subsets, each with a cost; minimize total cost."
- **Max coverage** — "I can pick at most k subsets; maximize the number of distinct elements covered."
- **Weighted bipartite matching** — "I have two groups (workers/jobs, students/schools, etc.) and need to match them one-to-one to maximize total value/profit." Use `weighted_bipartite_matching`.
- **Makespan scheduling** — "I have n jobs with processing times and m parallel machines; assign jobs to minimize the maximum machine load." Use `makespan_scheduling`.

### ILP fallback
- If a prompt is optimization-related but does not fit the five categories above,
    formulate a mixed integer linear program and call `mixed_ilp`.
- Extract:
    - variables with bounds/types (continuous, integer, binary),
    - replace natural language constraints with linear expressions (e.g., number of books is at most 10: `x <= 10`),
    - linear constraints using ASCII operators only (`<=`, `>=`, `==`) and never Unicode (`≤`, `≥`),
    - linear objective and sense (Max/Min) when the prompt asks to optimize.
- If the prompt is a feasibility problem (find any feasible solution), call `mixed_ilp`
  with variables and constraints, and omit objective.
- In your final response for mixed ILP, include:
    - a brief **Problem Summary** in plain language,
    - a **Model Summary** listing decision variables and objective,
    - a **Constraints Summary** that clearly restates each constraint.
- Then explain the solved variable values and objective in plain language.

## How to respond

When you receive a natural language problem description:
1. State which problem type you identified and why.
2. Show the extracted parameters as a brief table or list (e.g., items, weights, values, capacity).
3. Call the tool.
4. Present the solution in the user's original terms (e.g., "You should watch a movie ($15) and \
go to the concert ($50)..." not "Select items [1, 3]").
5. Include the objective value and any useful commentary (e.g., remaining budget, utilization rate).
6. If you used `mixed_ilp`, explicitly include sections for Problem Summary and Constraints Summary.
7. For feasibility-only mixed ILP, report feasibility status and one feasible assignment. 
In your final response for mixed ILP, include:
    - a brief **Problem Summary** in plain language,
    - a **Model Summary** listing decision variables and objective,
    - a **Constraints Summary** that clearly restates each constraint.
8. If the problem is not optimization-related or cannot be represented as a linear model,
say so and explain these supported types:
0/1 Knapsack, Bin packing, Weighted interval scheduling, Set cover, Max coverage, Weighted Bipartite Matching, Makespan Scheduling, mixed ILP."""

def _to_openai_tools(tools: list[dict]) -> list[dict]:
    """Convert our tool schemas to OpenAI function-calling format."""
    return [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
        for t in tools
    ]


def run(user_message: str) -> dict:
    """
    Run the agent loop.

    Args:
        user_message: The user's query.

    Returns:
        {"answer": str, "tool_logs": [{"solver", "algorithm", "guarantee",
         "complexity", "input_summary", "result", "error", "elapsed_s"}, ...]}
    """
    api_key, base_url, model = resolve_api_config()
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    tools = _to_openai_tools(TOOLS)
    tool_logs = []

    while True:
        response = client.chat.completions.create(
            model=model,
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )

        choice = response.choices[0]
        message = choice.message

        if not message.tool_calls:
            return {"answer": message.content or "", "tool_logs": tool_logs}

        # Append assistant message with tool calls
        messages.append(message)

        # Process each tool call
        for tc in message.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            meta = TOOL_META.get(name, {})

            log = {
                "solver": meta.get("display_name", name),
                "algorithm": meta.get("algorithm", ""),
                "guarantee": meta.get("guarantee", ""),
                "complexity": meta.get("complexity", ""),
                "input_summary": _format_args(name, args),
                "result": None,
                "error": None,
                "elapsed_s": None,
            }

            try:
                t0 = time.perf_counter()
                result = dispatch(name, args)
                elapsed = time.perf_counter() - t0
                content = json.dumps(result)
                log["result"] = content
                log["elapsed_s"] = round(elapsed, 4)
                log["julia_threads"] = julia_nthreads()
                if name == "ptas_knapsack":
                    log["chart"] = _knapsack_chart_data(args, result)
                elif name == "weighted_interval_scheduling":
                    log["chart"] = _interval_chart_data(args, result)
                elif name == "bin_packing":
                    log["chart"] = _bin_packing_chart_data(args, result)
                elif name == "makespan_scheduling":
                    log["chart"] = _makespan_chart_data(args, result)
            except Exception as e:
                content = json.dumps({"error": str(e)})
                log["error"] = str(e)

            tool_logs.append(log)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": content,
            })


def _knapsack_chart_data(args: dict, result: dict) -> dict:
    """Build chart data for a knapsack solution pie chart.

    The whole pie represents the knapsack capacity. Each selected item is a
    slice sized by its weight, and any unused capacity is shown as a grey slice.
    """
    capacity = args.get("capacity", 0)
    weights = args.get("weights", [])
    item_labels = args.get("labels", [])
    selected = result.get("items", [])  # 0-indexed

    sizes = [weights[i] for i in selected]
    labels = [
        (item_labels[i] if i < len(item_labels) else f"Item {i}")
        for i in selected
    ]

    used = sum(sizes)
    remaining = capacity - used
    if remaining > 0:
        sizes.append(remaining)
        labels.append("Unused Capacity")

    return {"type": "knapsack", "labels": labels, "sizes": sizes, "hasRemaining": remaining > 0}


def _interval_chart_data(args: dict, result: dict) -> dict:
    """Build chart data for a weighted interval scheduling timeline."""
    starts = args.get("start_times", [])
    ends = args.get("end_times", [])
    weights = args.get("weights", [])
    selected = set(result.get("selected_jobs", []))  # 0-indexed

    jobs = []
    for i in range(len(starts)):
        jobs.append({
            "label": f"Job {i} (w={weights[i]})",
            "start": starts[i],
            "end": ends[i],
            "selected": i in selected,
        })

    return {"type": "interval", "jobs": jobs}


def _bin_packing_chart_data(args: dict, result: dict) -> dict:
    """Build chart data for bin packing visualization."""
    items = args.get("items", [])
    bin_capacity = args.get("bin_capacity", 0)
    bins = result.get("bins", [])  # list of lists of 0-indexed item indices

    bin_data = []
    for i, bin_items in enumerate(bins):
        sizes = [items[idx] for idx in bin_items]
        bin_data.append({"label": f"Bin {i}", "sizes": sizes, "item_indices": bin_items})

    return {"type": "bin_packing", "bins": bin_data, "capacity": bin_capacity}


def _makespan_chart_data(args: dict, result: dict) -> dict:
    """Build chart data for makespan scheduling as a Gantt-style bar chart."""
    jobs = args.get("jobs", [])
    m = args.get("m", 1)
    machines = result.get("machines", [])  # list of lists of 0-indexed job indices

    machine_data = []
    for i, job_indices in enumerate(machines):
        machine_data.append({
            "label": str(i),
            "jobs": [{"index": j, "duration": jobs[j]} for j in job_indices],
        })

    return {"type": "makespan", "machines": machine_data, "makespan": result.get("makespan", 0)}


def _format_args(tool_name: str, args: dict) -> str:
    """Compact summary of tool arguments for display."""
    parts = []
    for k, v in args.items():
        if isinstance(v, list) and len(v) > 6:
            parts.append(f"{k}=[{len(v)} items]")
        elif isinstance(v, dict) and len(v) > 4:
            parts.append(f"{k}={{{len(v)} entries}}")
        else:
            parts.append(f"{k}={v}")
    return ", ".join(parts)


def _ensure_min_julia_version() -> None:
    ok = bool(jl.seval('VERSION >= v"1.12.0"'))
    if not ok:
        found = str(jl.seval("string(VERSION)"))
        raise RuntimeError(
            f"GraphBees requires Julia >= 1.12.0, but found Julia {found}. "
            "Set PYTHON_JULIACALL_EXE to a Julia 1.12+ binary."
        )