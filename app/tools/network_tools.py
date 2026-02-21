"""
Tool definitions for the agentic LLM to call.
Each tool wraps a JuliAlg function and returns a JSON-serializable result.
"""

from app.julia_bridge.runner import (
    bin_packing,
    makespan_scheduling,
    max_coverage,
    mixed_ilp,
    ptas_knapsack,
    set_cover,
    weighted_bipartite_matching,
    weighted_interval_scheduling,
)

TOOL_META = {
    "ptas_knapsack": {
        "display_name": "FPTAS Knapsack",
        "algorithm": "Value-Scaled Dynamic Programming (PTAS)",
        "guarantee": "(1 - epsilon)-approximation",
        "complexity": "O(n^2 / epsilon)",
    },
    "bin_packing": {
        "display_name": "Bin Packing",
        "algorithm": "First Fit Decreasing",
        "guarantee": "(11/9) OPT + O(1) bins",
        "complexity": "O(n log n)",
    },
    "weighted_interval_scheduling": {
        "display_name": "Weighted Interval Scheduling",
        "algorithm": "Dynamic Programming + Binary Search",
        "guarantee": "Exact",
        "complexity": "O(n log n)",
    },
    "set_cover": {
        "display_name": "Set Cover",
        "algorithm": "Greedy (cost-effectiveness ratio)",
        "guarantee": "O(ln n)-approximation",
        "complexity": "O(n * m)",
    },
    "max_coverage": {
        "display_name": "Max Coverage",
        "algorithm": "Greedy (marginal gain)",
        "guarantee": "(1 - 1/e)-approximation",
        "complexity": "O(k * n * m)",
    },
    "mixed_ilp": {
        "display_name": "Mixed ILP",
        "algorithm": "MILP via JuMP + HiGHS",
        "guarantee": "Exact (for solved model)",
        "complexity": "Problem-dependent",
    },
    "weighted_bipartite_matching": {
        "display_name": "Weighted Bipartite Matching",
        "algorithm": "LP Relaxation (exact for bipartite graph matching)",
        "guarantee": "Exact optimal",
        "complexity": "O(n^3) via LP",
    },
    "makespan_scheduling": {
        "display_name": "Makespan Scheduling",
        "algorithm": "Longest Processing Time (LPT)",
        "guarantee": "(4/3 - 1/(3m))-approximation",
        "complexity": "O(n log n)",
    },
}

TOOLS = [
    {
        "name": "ptas_knapsack",
        "description": "Solve 0/1 knapsack with (1-epsilon)-approximation. Faster than exact for large inputs.",
        "parameters": {
            "type": "object",
            "properties": {
                "capacity": {"type": "integer", "description": "Knapsack capacity"},
                "epsilon": {"type": "number", "description": "Approximation parameter (e.g. 0.1 for 90% optimality)"},
                "weights": {"type": "array", "items": {"type": "integer"}, "description": "Weight of each item"},
                "values": {"type": "array", "items": {"type": "integer"}, "description": "Value of each item"},
                "labels": {"type": "array", "items": {"type": "string"}, "description": "Optional label for each item (e.g. item name)"},
            },
            "required": ["capacity", "epsilon", "weights", "values"],
        },
    },
    {
        "name": "bin_packing",
        "description": "Pack items into fixed-capacity bins using Best-Fit Decreasing heuristic. Returns bin assignments.",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {"type": "array", "items": {"type": "integer"}, "description": "Size of each item"},
                "bin_capacity": {"type": "integer", "description": "Maximum capacity per bin"},
            },
            "required": ["items", "bin_capacity"],
        },
    },
    {
        "name": "weighted_interval_scheduling",
        "description": "Find maximum-weight set of non-overlapping intervals via DP. Returns selected jobs and total weight.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_times": {"type": "array", "items": {"type": "integer"}, "description": "Start time of each job"},
                "end_times": {"type": "array", "items": {"type": "integer"}, "description": "End time of each job"},
                "weights": {"type": "array", "items": {"type": "integer"}, "description": "Weight/value of each job"},
            },
            "required": ["start_times", "end_times", "weights"],
        },
    },
    {
        "name": "set_cover",
        "description": "Find approximate minimum-cost set cover using greedy algorithm. O(ln n) approximation.",
        "parameters": {
            "type": "object",
            "properties": {
                "subsets": {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}, "description": "Collection of subsets (each is a list of element ids)"},
                "costs": {"type": "array", "items": {"type": "number"}, "description": "Cost of each subset"},
            },
            "required": ["subsets", "costs"],
        },
    },
    {
        "name": "max_coverage",
        "description": "Select up to k subsets to maximize the number of covered elements. (1-1/e)-approximation.",
        "parameters": {
            "type": "object",
            "properties": {
                "subsets": {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}, "description": "Collection of subsets (each is a list of element ids)"},
                "k": {"type": "integer", "description": "Maximum number of subsets to select"},
            },
            "required": ["subsets", "k"],
        },
    },
    {
        "name": "weighted_bipartite_matching",
        "description": "Find maximum-weight matching in a bipartite graph. Exact solution via LP relaxation (integral for bipartite graphs). Use for assignment problems: workers to jobs, tasks to machines, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "left_nodes": {"type": "array", "items": {"type": "integer"}, "description": "Node IDs in the left partition (0-indexed). May overlap with right_nodes IDs — they are treated as independent label spaces."},
                "right_nodes": {"type": "array", "items": {"type": "integer"}, "description": "Node IDs in the right partition (0-indexed). May overlap with left_nodes IDs — they are treated as independent label spaces."},
                "edges": {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}, "description": "List of [u, v] edges where u is a left node ID and v is a right node ID."},
                "weights": {"type": "array", "items": {"type": "number"}, "description": "Optional weight per edge, parallel to the edges list. Defaults to 1.0 per edge."},
            },
            "required": ["left_nodes", "right_nodes", "edges"],
        },
    },
    {
        "name": "makespan_scheduling",
        "description": "Schedule n jobs on m identical parallel machines to minimize makespan (total completion time) using the LPT heuristic. (4/3 - 1/(3m))-approximation guarantee.",
        "parameters": {
            "type": "object",
            "properties": {
                "jobs": {"type": "array", "items": {"type": "number"}, "description": "Processing time of each job"},
                "m": {"type": "integer", "description": "Number of machines"},
            },
            "required": ["jobs", "m"],
        },
    },
    {
        "name": "mixed_ilp",
        "description": "Solve a mixed ILP model formulated from natural language using JuMP + HiGHS.",
        "parameters": {
            "type": "object",
            "properties": {
                "variables": {
                    "type": "array",
                    "description": "Decision variables",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Variable name, e.g. x"},
                            "lower_bound": {"type": "number", "description": "Optional lower bound"},
                            "upper_bound": {"type": "number", "description": "Optional upper bound"},
                            "var_type": {"type": "string", "description": "continuous|integer|binary", "default": "continuous"},
                        },
                        "required": ["name"],
                    },
                },
                "constraints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Linear constraints using ASCII operators only (<=, >=, ==), e.g. ['2x + y <= 10', 'x + 3y <= 12']",
                },
                "objective": {
                    "type": "string",
                    "description": "Optional linear objective expression, e.g. '3x + 5y'. Omit for feasibility-only models.",
                },
                "sense": {
                    "type": "string",
                    "description": "Optimization sense: Max or Min",
                    "default": "Max",
                },
            },
            "required": ["variables", "constraints"],
        },
    },
]


def dispatch(tool_name: str, args: dict):
    """Route a tool call to the right Julia bridge function."""
    if tool_name == "ptas_knapsack":
        return ptas_knapsack(args["capacity"], args["epsilon"], args["weights"], args["values"])
    elif tool_name == "bin_packing":
        return bin_packing(args["items"], args["bin_capacity"])
    elif tool_name == "weighted_interval_scheduling":
        return weighted_interval_scheduling(args["start_times"], args["end_times"], args["weights"])
    elif tool_name == "set_cover":
        return set_cover(args["subsets"], args["costs"])
    elif tool_name == "max_coverage":
        return max_coverage(args["subsets"], args["k"])
    elif tool_name == "weighted_bipartite_matching":
        edges = [tuple(e) for e in args["edges"]]
        weight_list = args.get("weights")
        weights = (
            {tuple(e): float(w) for e, w in zip(args["edges"], weight_list)}
            if weight_list is not None
            else None
        )
        return weighted_bipartite_matching(args["left_nodes"], args["right_nodes"], edges, weights)
    elif tool_name == "makespan_scheduling":
        return makespan_scheduling(args["jobs"], args["m"])
    elif tool_name == "mixed_ilp":
        return mixed_ilp(
            args["variables"],
            args["constraints"],
            args.get("objective"),
            args.get("sense", "Max"),
        )
    else:
        raise ValueError(f"Unknown tool: {tool_name}")
