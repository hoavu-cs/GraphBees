"""
Bridge to call JuliAlg functions from Python via juliacall.
"""

import json
import os
import re
import shutil
import tempfile
from typing import Optional

"""
This module bootstraps and manages a self-contained Julia runtime
environment from Python using `juliacall`.

What this code does:

1. Configures Julia runtime behavior
   - Enables automatic thread selection.
   - Ensures Julia properly handles interrupt signals (e.g., Ctrl+C).

2. Creates an isolated runtime directory
   - Uses GRAPHBEES_RUNTIME_DIR if provided.
   - Otherwise falls back to the system temporary directory.
   - All Julia-related files (packages, depot, project) live here.
   - Prevents polluting the user's global Julia installation.

3. Sets Julia environment variables
   - PYTHON_JULIAPKG_PROJECT: where juliacall stores its Julia project.
   - JULIA_DEPOT_PATH: where Julia installs packages and artifacts.
   - Both are redirected into the runtime directory.

4. Manages the custom JuliAlgEnv project
   - Attempts to use the source JuliAlgEnv if writable.
   - If running in a read-only environment (e.g., Render),
     copies JuliAlgEnv into the writable runtime directory.
   - Ensures the Julia environment is always writable.

5. Initializes Julia via juliacall
   - Activates the JuliAlgEnv project.
   - Checks whether required packages are declared:
       - JuliAlg
       - Graphs
       - JuMP
       - HiGHS
   - Installs any missing packages automatically.
   - Loads required Julia modules into the runtime.

Overall goal:
Provide a reproducible, isolated, self-healing Julia environment
that works in local development and read-only deployment platforms
(e.g., Render) without requiring manual Julia setup.
"""


# Tell Julia to use as many CPU threads as it can safely use.
os.environ["PYTHON_JULIACALL_THREADS"] = "auto"

# Let Julia handle process signals correctly (important for clean startup/shutdown).
if os.name == "posix" and os.uname().sysname == "Darwin":
    os.environ.setdefault("PYTHON_JULIACALL_HANDLE_SIGNALS", "no")
else:
    os.environ.setdefault("PYTHON_JULIACALL_HANDLE_SIGNALS", "yes")

# Pick a writable base folder for all runtime Julia data.
# If GRAPHBEES_RUNTIME_DIR is set, use it; otherwise use the system temp folder.
_RUNTIME_ROOT = os.path.join(
    os.environ.get("GRAPHBEES_RUNTIME_DIR", tempfile.gettempdir()),
    "graphbees_runtime",
)

# Create that runtime folder if it does not exist yet.
os.makedirs(_RUNTIME_ROOT, exist_ok=True)

# Where juliapkg stores its Julia project metadata.
# setdefault means: keep user-provided value if already set.
os.environ.setdefault("PYTHON_JULIAPKG_PROJECT", os.path.join(_RUNTIME_ROOT, "juliapkg"))

# Where Julia stores downloaded packages/compiled artifacts (depot/cache).
os.environ.setdefault("JULIA_DEPOT_PATH", os.path.join(_RUNTIME_ROOT, "julia_depot"))

# Source Julia environment bundled in this repo (if present).
_SOURCE_JULIALG_ENV = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "JuliAlgEnv")
)

# Runtime Julia environment location (always writable target).
_RUNTIME_JULIALG_ENV = os.path.join(_RUNTIME_ROOT, "JuliAlgEnv")

# If the source env exists and is writable, use it directly (best for local dev).
if os.path.isdir(_SOURCE_JULIALG_ENV) and os.access(_SOURCE_JULIALG_ENV, os.W_OK):
    _JULIALG_ENV = _SOURCE_JULIALG_ENV
else:
    # If source env exists but runtime copy does not, copy it once.
    # This is useful on cloud where source may be read-only.
    if os.path.isdir(_SOURCE_JULIALG_ENV) and not os.path.exists(_RUNTIME_JULIALG_ENV):
        shutil.copytree(_SOURCE_JULIALG_ENV, _RUNTIME_JULIALG_ENV)

    # Ensure runtime env folder exists even if source env is missing.
    os.makedirs(_RUNTIME_JULIALG_ENV, exist_ok=True)

    # Use runtime env as the active Julia environment.
    _JULIALG_ENV = _RUNTIME_JULIALG_ENV

from juliacall import Main as jl


def init_julialg():
    """Activate the JuliAlgEnv environment, installing packages if needed."""

    # Import Pkg once
    jl.seval("import Pkg")

    # Activate environment safely (no string interpolation!)
    jl.Pkg.activate(_JULIALG_ENV)

    # Check required packages
    installed = jl.seval("""
        deps = keys(Pkg.project().dependencies)
        ("JuliAlg" in deps, "Graphs" in deps, "JuMP" in deps, "HiGHS" in deps)
    """)

    has_julialg, has_graphs, has_jump, has_highs = map(bool, installed)

    # Add any missing packages before instantiating.
    # JuliAlg must be added via URL (not registered in the General registry),
    # so Pkg.add must run before Pkg.instantiate to ensure the Manifest is valid.
    if not all([has_julialg, has_graphs, has_jump, has_highs]):
        print("Installing missing Julia packages into JuliAlgEnv...")

        if not has_julialg:
            jl.Pkg.add(url="https://github.com/hoavu-cs/JuliAlg.git")

        if not has_graphs:
            jl.Pkg.add("Graphs")

        if not has_jump:
            jl.Pkg.add("JuMP")

        if not has_highs:
            jl.Pkg.add("HiGHS")

    # Instantiate after packages are guaranteed to be in the Manifest.
    # If the Manifest was written by a different Julia version, delete and retry.
    try:
        jl.Pkg.instantiate()
    except Exception:
        manifest = os.path.join(_JULIALG_ENV, "Manifest.toml")
        if os.path.exists(manifest):
            os.remove(manifest)
        jl.Pkg.add(url="https://github.com/hoavu-cs/JuliAlg.git")
        jl.Pkg.add("Graphs")
        jl.Pkg.add("JuMP")
        jl.Pkg.add("HiGHS")
        jl.Pkg.instantiate()

    jl.seval("using JuliAlg, Graphs")


def julia_nthreads() -> int:
    """Return the number of Julia threads."""
    return int(jl.seval("Threads.nthreads()"))


def influence_maximization(edges: list[tuple[int, int]], weights: dict[tuple[int, int], float], k: int, n_simulations: int = 10_000) -> dict:
    """Find k seed nodes that maximize influence spread (Independent Cascade)."""
    edges1 = _to_1indexed(edges)
    weights1 = {(u + 1, v + 1): w for (u, v), w in weights.items()}
    _build_digraph = f"""
    begin
        g = SimpleDiGraph({_max_node(edges1)})
        {_add_edges_code(edges1)}
        w = Dict({_weights_code(weights1)})
        solution, spread = influence_maximization_ic(g, w, {k}, 1000, {n_simulations})
        (collect(solution), spread)
    end
    """
    result = jl.seval(_build_digraph)
    return {"seed_nodes": [int(x) - 1 for x in result[0]], "expected_spread": float(result[1])}


def densest_subgraph(edges: list[tuple[int, int]], directed: bool = False) -> dict:
    """Find the densest subgraph."""
    edges1 = _to_1indexed(edges)
    graph_type = "SimpleDiGraph" if directed else "SimpleGraph"
    code = f"""
    begin
        g = {graph_type}({_max_node(edges1)})
        {_add_edges_code(edges1)}
        nodes, density = densest_subgraph(g)
        (collect(nodes), density)
    end
    """
    result = jl.seval(code)
    return {"nodes": [int(x) - 1 for x in result[0]], "density": float(result[1])}


def k_core_decomposition(edges: list[tuple[int, int]]) -> dict[int, int]:
    """Compute k-core decomposition. Returns node -> core number mapping."""
    edges1 = _to_1indexed(edges)
    code = f"""
    begin
        g = SimpleGraph({_max_node(edges1)})
        {_add_edges_code(edges1)}
        k_core_decomposition(g)
    end
    """
    result = jl.seval(code)
    return {int(k) - 1: int(v) for k, v in result.items()}


def betweenness_centrality(edges: list[tuple[int, int]], normalized: bool = True) -> list[float]:
    """Compute betweenness centrality for all nodes. Returns list where index i = node i."""
    edges1 = _to_1indexed(edges)
    code = f"""
    begin
        g = SimpleGraph({_max_node(edges1)})
        {_add_edges_code(edges1)}
        collect(bw_centrality(g; normalized={"true" if normalized else "false"}))
    end
    """
    result = jl.seval(code)
    return [float(x) for x in result]


def pagerank(edges: list[tuple[int, int]], alpha: float = 0.85) -> list[float]:
    """Compute PageRank scores for all nodes. Returns list where index i = node i."""
    edges1 = _to_1indexed(edges)
    code = f"""
    begin
        g = SimpleGraph({_max_node(edges1)})
        {_add_edges_code(edges1)}
        collect(pagerank(g; α={alpha}))
    end
    """
    result = jl.seval(code)
    return [float(x) for x in result]


# --- combinatorial optimization ---


def exact_knapsack(capacity: int, weights: list[int], values: list[int]) -> dict:
    """Solve 0/1 knapsack exactly via DP."""
    code = f"""
    begin
        best_v, items = exact_knapsack({capacity}, {_jl_vector(weights)}, {_jl_vector(values)})
        (best_v, collect(items))
    end
    """
    result = jl.seval(code)
    return {"value": int(result[0]), "items": [int(x) - 1 for x in result[1]]}


def ptas_knapsack(capacity: int, epsilon: float, weights: list[int], values: list[int]) -> dict:
    """Solve 0/1 knapsack with (1-epsilon)-approximation."""
    code = f"""
    begin
        val, items = ptas_knapsack({capacity}, {epsilon}, {_jl_vector(weights)}, {_jl_vector(values)})
        (val, collect(items))
    end
    """
    result = jl.seval(code)
    return {"value": int(result[0]), "items": [int(x) - 1 for x in result[1]]}


def bin_packing(items: list[int], bin_capacity: int) -> dict:
    """Pack items into bins using Best-Fit Decreasing."""
    code = f"""
    begin
        num_bins, bins = bin_packing({_jl_vector(items)}, {bin_capacity})
        (num_bins, [collect(b) for b in bins])
    end
    """
    result = jl.seval(code)
    return {
        "num_bins": int(result[0]),
        "bins": [[int(x) - 1 for x in b] for b in result[1]],
    }


def weighted_interval_scheduling(start_times: list[int], end_times: list[int], weights: list[int]) -> dict:
    """Find max-weight non-overlapping intervals."""
    code = f"""
    begin
        max_w, jobs = weighted_interval_scheduling({_jl_vector(start_times)}, {_jl_vector(end_times)}, {_jl_vector(weights)})
        (max_w, collect(jobs))
    end
    """
    result = jl.seval(code)
    return {"max_weight": int(result[0]), "selected_jobs": [int(x) - 1 for x in result[1]]}


def set_cover(subsets: list[list[int]], costs: list[float]) -> dict:
    """Find approximate minimum-cost set cover."""
    subsets_code = "[" + ", ".join(_jl_vector(s) for s in subsets) + "]"
    costs_code = "[" + ", ".join(str(float(c)) for c in costs) + "]"
    code = f"""
    begin
        total_cost, selected = set_cover({subsets_code}, {costs_code})
        (total_cost, collect(selected))
    end
    """
    result = jl.seval(code)
    return {"total_cost": float(result[0]), "selected_subsets": [int(x) - 1 for x in result[1]]}


def makespan_scheduling(jobs: list[float], m: int) -> dict:
    """Schedule jobs on m machines to minimize makespan using LPT heuristic."""
    code = f"""
    begin
        makespan, assignments = lpt_makespan({_jl_vector([float(j) for j in jobs])}, {m})
        (makespan, collect(assignments))
    end
    """
    result = jl.seval(code)
    assignments = [int(x) - 1 for x in result[1]]
    machines: list[list[int]] = [[] for _ in range(m)]
    for job_idx, machine_idx in enumerate(assignments):
        machines[machine_idx].append(job_idx)
    return {
        "makespan": float(result[0]),
        "assignments": assignments,
        "machines": machines,
    }


def max_coverage(subsets: list[list[int]], k: int) -> dict:
    """Select up to k subsets to maximize element coverage."""
    subsets_code = "[" + ", ".join(_jl_vector(s) for s in subsets) + "]"
    code = f"""
    begin
        covered, selected = max_coverage({subsets_code}, {k})
        (covered, collect(selected))
    end
    """
    result = jl.seval(code)
    return {"num_covered": int(result[0]), "selected_subsets": [int(x) - 1 for x in result[1]]}


def weighted_bipartite_matching(
    left_nodes: list[int],
    right_nodes: list[int],
    edges: list[tuple[int, int]],
    weights: Optional[dict[tuple[int, int], float]] = None,
) -> dict:
    """Find maximum-weight bipartite matching (exact via LP relaxation).

    left_nodes and right_nodes are treated as independent label spaces and
    may overlap (e.g. both can use 0-based indices). They are remapped to
    disjoint internal IDs before being passed to Julia.
    """
    # Remap to disjoint 1-indexed Julia node IDs:
    #   left node i  -> rank in left_nodes list  + 1
    #   right node j -> rank in right_nodes list + len(left_nodes) + 1
    nl = len(left_nodes)
    left_map  = {u: i + 1       for i, u in enumerate(left_nodes)}
    right_map = {v: nl + i + 1  for i, v in enumerate(right_nodes)}

    left1  = list(left_map.values())
    right1 = list(right_map.values())
    n = nl + len(right_nodes)

    edges1 = [(left_map[u], right_map[v]) for u, v in edges]

    if weights:
        weights1 = {(left_map[u], right_map[v]): float(w) for (u, v), w in weights.items()}
        weights_arg = f"Dict({_weights_code(weights1)})"
    else:
        weights_arg = "Dict{Tuple{Int,Int}, Float64}()"

    # Inverse maps: internal Julia ID -> original Python label
    inv_left  = {v: k for k, v in left_map.items()}
    inv_right = {v: k for k, v in right_map.items()}

    jl.seval("using JuMP\nusing HiGHS")
    code = f"""
    begin
        g = SimpleGraph({n})
        {_add_edges_code(edges1)}
        L = {_jl_vector(left1)}
        R = {_jl_vector(right1)}
        w = {weights_arg}
        total_weight, matched = weighted_bipartite_matching(g, L, R; weights=w)
        (total_weight, [(e[1], e[2]) for e in matched])
    end
    """
    result = jl.seval(code)
    return {
        "total_weight": float(result[0]),
        "matched_edges": [
            [inv_left[int(e[0])], inv_right[int(e[1])]]
            for e in result[1]
        ],
    }


def mixed_ilp(variables: list[dict], constraints: list[str], objective: Optional[str] = None, sense: str = "Max") -> dict:
    """Solve a mixed ILP model via JuMP + HiGHS.

    Args:
        variables: [{"name", "lower_bound", "upper_bound", "var_type"}]
        constraints: list of linear constraints as strings, e.g. "2x + y <= 10"
        objective: optional linear expression string, e.g. "3x + 5y"
        sense: "Max" or "Min"
    """
    if not variables:
        raise ValueError("variables must be non-empty")
    if not constraints:
        raise ValueError("constraints must be non-empty")

    has_objective = objective is not None and str(objective).strip() != ""
    if has_objective and sense not in {"Max", "Min"}:
        raise ValueError("sense must be 'Max' or 'Min'")

    decl_lines: list[str] = []
    post_lines: list[str] = []
    value_pairs: list[str] = []

    for var in variables:
        name = str(var.get("name", "")).strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"Invalid variable name: {name!r}")

        decl_lines.append(f"@variable(model, {name})")
        value_pairs.append(f"{_jl_str(name)} => value({name})")

        lb = var.get("lower_bound")
        ub = var.get("upper_bound")
        if lb is not None:
            post_lines.append(f"set_lower_bound({name}, {float(lb)})")
        if ub is not None:
            post_lines.append(f"set_upper_bound({name}, {float(ub)})")

        vtype = str(var.get("var_type", "continuous")).lower()
        if vtype == "integer":
            post_lines.append(f"set_integer({name})")
        elif vtype == "binary":
            post_lines.append(f"set_binary({name})")
        elif vtype != "continuous":
            raise ValueError(f"Unsupported var_type: {vtype}")

    constraints_vec_code = "[" + ", ".join(_jl_str(c) for c in constraints) + "]"
    objective_code = _jl_str(objective) if has_objective else "nothing"
    objective_sense = sense if has_objective else "Min"
    decl_block = "\n        ".join(decl_lines)
    post_block = "\n        ".join(post_lines)
    value_pairs_block = ", ".join(value_pairs)

    jl.seval("using JuMP\nusing HiGHS")
    model_code = f"""
    begin
        model = Model(HiGHS.Optimizer)
        {decl_block}
        {post_block}
        constraint_texts = {constraints_vec_code}
        for c_str in constraint_texts
            c_expr = Meta.parse(c_str)
            eval(:(@constraint(model, $c_expr)))
        end
        if {str(has_objective).lower()}
            obj_expr = Meta.parse({objective_code})
            eval(:(@objective(model, {objective_sense}, $obj_expr)))
        else
            @objective(model, Min, 0)
        end
        optimize!(model)
        status = string(termination_status(model))
        obj = has_values(model) ? objective_value(model) : nothing
        vals = has_values(model) ? Dict({value_pairs_block}) : Dict()
        (status, obj, vals)
    end
    """
    result = jl.seval(model_code)
    status = str(result[0])
    objective_value = None if result[1] is None else float(result[1])
    var_values = {str(k): float(v) for k, v in result[2].items()}
    return {
        "status": status,
        "mode": "optimization" if has_objective else "feasibility",
        "objective_value": objective_value,
        "variable_values": var_values,
    }


# --- helpers for building Julia code strings ---


def _jl_vector(items: list) -> str:
    """Convert a Python list to a Julia vector literal."""
    return "[" + ", ".join(str(x) for x in items) + "]"



def _to_1indexed(edges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Shift edges from 0-indexed (Python) to 1-indexed (Julia)."""
    return [(u + 1, v + 1) for u, v in edges]


def _max_node(edges: list[tuple[int, int]]) -> int:
    return max(max(u, v) for u, v in edges)


def _add_edges_code(edges: list[tuple[int, int]]) -> str:
    return "\n        ".join(f"add_edge!(g, {u}, {v})" for u, v in edges)


def _weights_code(weights: dict[tuple[int, int], float]) -> str:
    return ", ".join(f"({u},{v}) => {w}" for (u, v), w in weights.items())


def _jl_str(text: str) -> str:
    """Return a safely quoted Julia string literal."""
    return json.dumps(str(text))

