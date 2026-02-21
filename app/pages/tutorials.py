"""Tutorials page with guided optimization examples."""

import os
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so `app.*` imports work when
# Streamlit runs this page as a standalone script.
_repo_root = str(Path(__file__).resolve().parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import streamlit as st

from app.sidebar import maybe_shutdown, render_chat_download, render_sidebar
from app.styles import inject_shared_css

KNAPSACK_EXAMPLE = """
I have a budget of $1000. 
Projects: 
- Project A costs $300 with value 80, 
- Project B costs $200 with value 50, 
- Project C costs $400 with value 120, 
- Project D costs $500 with value 150, 
- Project E costs $100 with value 30. 
Which projects should I fund to maximize total value? Use epsilon=0.1.
"""

BIN_PACKING_EXAMPLE = """
You’re planning your work for the next few days. Each day has a maximum capacity of **100 minutes** of focused work. 
You have a list of tasks that must each be completed in a single day (you can’t split a task across days). 
The task durations (in minutes) are: 
[45, 30, 25, 20, 15, 10, 5, 5, 5, 5, 5, 5]. 
You can schedule tasks into days as long as the total minutes scheduled in any day does not exceed 100. 
What is the minimum number of days needed to complete all tasks?
"""

WEIGHTED_INTERVAL_SCHEDULING_EXAMPLE = """
Schedule meetings to maximize total importance. 
Meetings: 
- 1 (9-11, importance 5), 
- 2 (10-12, importance 6), 
- 3 (11-13, importance 7), 
- 4 (14-16, importance 8), 
- 5 (15-17, importance 4). Which non-overlapping meetings should I attend?
"""

SET_COVER_EXAMPLE = """You are designing a city-wide environmental monitoring system for **15 locations** labeled 1 through 15. Each available sensor model can monitor a different set of locations, and installation costs vary. Your goal is to select a combination of sensors that ensures **all 15 locations are covered** while minimizing total installation cost.
The available sensors are:
- Sensor A monitors locations {1, 2} and costs $60.
- Sensor B monitors locations {2, 3, 4, 5} and costs $140.
- Sensor C monitors locations {1, 6, 7, 8, 9} and costs $200.
- Sensor D monitors locations {4, 10} and costs $75.
- Sensor E monitors locations {5, 8, 11, 12} and costs $150.
- Sensor F monitors locations {6, 10, 13} and costs $95.
- Sensor G monitors locations {7, 14} and costs $70.
- Sensor H monitors locations {9, 12, 15} and costs $110.
- Sensor I monitors locations {3, 11, 13, 14, 15} and costs $180.
- Sensor J monitors location {10} and costs $40.

Which set of sensors should you install to cover all 15 locations at the minimum total cost?
"""

MAX_COVER_EXAMPLE = """You are designing a city-wide environmental monitoring system for **15 locations** labeled 1 through 15. Each available sensor model can monitor a different set of locations, and installation costs vary. Your goal is to select a combination of sensors that ensures **all 15 locations are covered** while minimizing total installation cost.
The available sensors are:
- Sensor A monitors locations {1, 2} and costs $60.
- Sensor B monitors locations {2, 3, 4, 5} and costs $140.
- Sensor C monitors locations {1, 6, 7, 8, 9} and costs $200.
- Sensor D monitors locations {4, 10} and costs $75.
- Sensor E monitors locations {5, 8, 11, 12} and costs $150.
- Sensor F monitors locations {6, 10, 13} and costs $95.
- Sensor G monitors locations {7, 14} and costs $70.
- Sensor H monitors locations {9, 12, 15} and costs $110.
- Sensor I monitors locations {3, 11, 13, 14, 15} and costs $180.
- Sensor J monitors location {10} and costs $40.

Choose at most 5 sensors to cover as many distinct locations as possible. 
Which sensors should you pick, and how many locations will they cover?
"""

MILP_EXAMPLE = """
Goal: Maximize total calories while staying under 20g fat.
Constraints: At most one rice, one beans, and one protein.

PROTEINS
- Chicken Al Pastor - 200 cal - 11g fat - 23g protein - 4g carbs
- Chicken - 180 cal - 7g fat - 32g protein - 0g carbs
- Steak - 150 cal - 6g fat - 21g protein - 1g carbs
- Beef Barbacoa - 170 cal - 7g fat - 24g protein - 2g carbs
- Carnitas - 210 cal - 12g fat - 23g protein - 0g carbs
- Sofritas - 150 cal - 10g fat - 8g protein - 9g carbs
- Veggie - 0 cal - 0g fat - 0g protein - 0g carbs

RICE
- White Rice - 210 cal - 4g fat - 4g protein - 40g carbs
- Brown Rice - 210 cal - 6g fat - 4g protein - 36g carbs

BEANS
- Black Beans - 130 cal - 2g fat - 8g protein - 22g carbs
- Pinto Beans - 130 cal - 2g fat - 8g protein - 21g carbs

TOPPINGS AND SALSAS
- Red Chimichurri - 190 cal - 17g fat - 1g protein - 8g carbs
- Guacamole - 230 cal - 22g fat - 2g protein - 8g carbs
- Fresh Tomato Salsa - 25 cal - 0g fat - 0g protein - 4g carbs
- Roasted Chili-Corn Salsa - 80 cal - 2g fat - 3g protein - 16g carbs
- Tomatillo-Green Chili Salsa - 15 cal - 0g fat - 0g protein - 4g carbs
- Tomatillo-Red Chili Salsa - 30 cal - 0g fat - 0g protein - 4g carbs
- Sour Cream - 110 cal - 9g fat - 2g protein - 2g carbs
- Fajita Veggies - 20 cal - 0g fat - 1g protein - 5g carbs
- Cheese - 110 cal - 8g fat - 6g protein - 1g carbs
- Romaine Lettuce - 5 cal - 0g fat - 0g protein - 1g carbs
- Queso Blanco - 120 cal - 9g fat - 5g protein - 4g carbs
"""

FEASIBILITY_MILP_EXAMPLE = """
You run a small custom furniture workshop and need to find any production plan that meets your resource limits. 
Standard desks must be produced in whole units, while premium cabinets and add-on packages can be produced in fractional batches. 
Let x = number of standard desks (x is a nonnegative integer), y = number of premium cabinets (y is a nonnegative continuous variable), and z = number of decorative add-on packages (z is a nonnegative continuous variable). 
Find any values of x, y, and z that satisfy all constraints: 
carpentry labor hours: 6x + 4y + 1z <= 60; 
finishing hours: 3x + 5y + 2z <= 55; 
storage space: 4x + 6y + 1z <= 70; 
and also meet these minimum commitments: x >= 5, y >= 2.5, z >= 10. 
Report one feasible solution (x, y, z) if it exists, or report that the model is infeasible.
"""

UNWEIGHTED_BIPARTITE_MATCHING_EXAMPLE = """
You are organizing a volunteer schedule for a community event.

You have a list of volunteer names and a list of shift names. 
Each volunteer is available for certain shifts. 
Each volunteer can work at most one shift, and each shift can be assigned to at most one volunteer. 
Your goal is to assign volunteers to shifts to maximize the number of filled shifts.

Input format:

* First line: A comma-separated list of volunteer names
* Second line: A space-separated list of shift names
* Next lines: volunteer_name, shift_name (indicating that the volunteer is available for that shift)

Output format:

* First line: K, the maximum number of assignments
* Next K lines: volunteer_name, shift_name (each volunteer appears at most once, each shift appears at most once)

Input:
Alice, Bob, Charlie, Dana
Morning, Afternoon, Evening, Night
- Alice, Morning
- Alice, Evening
- Bob, Afternoon
- Charlie, Evening
- Charlie, Night
- Dana, Night
"""

WEIGHTED_BIPARTITE_MATCHING_EXAMPLE = """
You are coordinating a small team for a one-day event.

You have a list of people and a list of tasks. 
Each person can be assigned to at most one task, and each task can be assigned to at most one person. 
If a person is assigned to a task, you gain a certain number of points (a "fit score") representing how good that person is for that task (skill, preference, speed, etc.). 
Not every person can do every task. Your goal is to choose assignments that maximize the total fit score.

Input format:

* First line: a comma-separated list of people names
* Second line: a comma-separated list of task names
* Next lines: person_name, task_name, score

Output format:

* First line: BestTotalScore (maximum possible total score)
* Second line: K (number of assignments selected)
* Next K lines: person_name, task_name, score (each person appears at most once, each task appears at most once)

Input:
Alice, Bob, Charlie, Dana
Register, Setup, Cleanup, SpeakerSupport

- Alice, Register, 9
- Alice, Setup, 6
- Bob, Setup, 8
- Bob, Cleanup, 7
- Charlie, Cleanup, 10
- Charlie, SpeakerSupport, 5
- Dana, Register, 4
- Dana, Setup, 7
- Dana, SpeakerSupport, 9
"""


# Algorithm categories and their tools with full example prompts
ALGORITHM_CATEGORIES = {
    "Combinatorial Optimization": [
        {
            "name": "Knapsack (FPTAS)",
            "description": "Select items with maximum value within capacity",
            "high_level": "Choose the best subset of options under a single budget/capacity limit to maximize total value.",
            "algorithm": "Value-Scaled Dynamic Programming",
            "guarantee": "(1 - ε)-approximation",
            "complexity": "O(n^2 / ε)",
            "full_example": KNAPSACK_EXAMPLE,

            "example_prompts": [
                "I have a budget of $1000, which projects should I fund?",
                "Pack the most valuable items in a suitcase with 50kg limit",
                "Select investments with maximum return under $10,000 budget"
            ]
        },
        {
            "name": "Bin Packing",
            "description": "Pack items into minimum number of fixed-capacity bins",
            "high_level": "Group items into containers so no container exceeds capacity while minimizing how many containers are used.",
            "algorithm": "First Fit Decreasing",
            "guarantee": "(11/9) OPT + 1 bins",
            "complexity": "O(n log n)",
            "full_example": BIN_PACKING_EXAMPLE,
            "example_prompts": [
                "Pack these boxes into the fewest shipping containers",
                "Schedule tasks into minimum number of time slots",
                "Allocate files to disks with 1TB capacity each"
            ]
        },
        {
            "name": "Weighted Interval Scheduling",
            "description": "Select non-overlapping intervals with maximum total weight",
            "high_level": "Pick a set of time intervals that do not overlap and gives the highest total priority/value.",
            "algorithm": "Dynamic Programming + Binary Search",
            "guarantee": "Exact",
            "complexity": "O(n log n)",
            "full_example": WEIGHTED_INTERVAL_SCHEDULING_EXAMPLE,
            "example_prompts": [
                "Schedule meetings to maximize total importance",
                "Select TV shows to record for maximum enjoyment",
                "Choose non-conflicting events with highest priority"
            ]
        },
        {
            "name": "Set Cover",
            "description": "Cover all elements using minimum-cost subsets",
            "high_level": "Select a minimum-cost collection of sets so that every required element is covered at least once.",
            "algorithm": "Greedy (cost-effectiveness ratio)",
            "guarantee": "O(ln n)-approximation",
            "complexity": "O(n * m)",
            "full_example": SET_COVER_EXAMPLE,
            "example_prompts": [
                "Select minimum-cost set of sensors to cover all locations",
                "Choose fewest courses to cover all required topics",
                "Select radio stations to cover all cities at minimum cost"
            ]
        },
        {
            "name": "Max Coverage",
            "description": "Select up to k subsets to maximize covered elements",
            "high_level": "With a fixed number of picks, choose sets that cover as many distinct elements as possible.",
            "algorithm": "Greedy (marginal gain)",
            "guarantee": "(1 - 1/e)-approximation",
            "complexity": "O(k * n * m)",
            "full_example": MAX_COVER_EXAMPLE,
            "example_prompts": [
                "Choose 3 advertising channels to reach maximum customers",
                "Select 5 stores to serve the most neighborhoods",
                "Pick 10 features to satisfy the most user requirements"
            ]
        },
        {
            "name": "Mixed Integer Linear Programming",
            "description": "Formulate and solve a mixed integer linear program",
            "high_level": "When a problem doesn't match built-in templates, model it with linear variables, constraints, and an objective, then solve exactly with an ILP solver.",
            "algorithm": "JuMP + HiGHS (MILP)",
            "guarantee": "Exact (for solved model)",
            "complexity": "Problem-dependent",
            "full_example": MILP_EXAMPLE,
            "example_prompts": [
                "Formulate and solve this linear optimization model with constraints and objective",
                "Use mixed ILP for this scheduling model with integer decision variables",
                "This doesn’t match knapsack/bin packing; convert it to an ILP and solve"
            ]
        },
        {
            "name": "Mixed Integer Linear Programming Feasibility",
            "description": "Formulate and solve a mixed integer linear program",
            "high_level": "When a feasibility (i.e., finding any solution that satisfies all constraints) problem doesn't match built-in templates, model it with linear variables, constraints, then solve exactly with an ILP solver.",
            "algorithm": "JuMP + HiGHS (MILP)",
            "guarantee": "Exact (for solved model)",
            "complexity": "Problem-dependent",
            "full_example": FEASIBILITY_MILP_EXAMPLE,
            "example_prompts": [
                "Formulate and solve this linear optimization model with constraints and objective",
                "Use mixed ILP for this scheduling model with integer decision variables",
                "This doesn’t match knapsack/bin packing; convert it to an ILP and solve"
            ]
        },
        {
            "name": "Unweighted Bipartite Matching",
            "description": "Match elements from two groups to maximize total weight",
            "high_level": "Given two sets of entities and weighted edges between them, find the best one-to-one matching that maximizes total number of matches.",
            "algorithm": "LP Relaxation (exact for bipartite graphs)",
            "guarantee": "Exact optimal",
            "complexity": "O(n^3) via LP",
            "full_example": UNWEIGHTED_BIPARTITE_MATCHING_EXAMPLE,
            "example_prompts": [
                "Assign volunteers to shifts to maximize filled shifts",
                "Match students to schools based on preferences and capacities",
                "Pair workers to tasks for maximum total efficiency"
            ]
        },
        {
            "name": "Weighted Bipartite Matching",
            "description": "Match elements from two groups to maximize total weight",
            "high_level": "Given two sets of entities and weighted edges between them, find the best one-to-one matching that maximizes total weight.",
            "algorithm": "LP Relaxation (exact for bipartite graphs)",
            "guarantee": "Exact optimal",
            "complexity": "O(n^3) via LP",
            "full_example": WEIGHTED_BIPARTITE_MATCHING_EXAMPLE,
            "example_prompts": [
                "Assign volunteers to shifts to maximize total fit score",
                "Match students to schools based on preferences and capacities",
                "Pair workers to tasks for maximum total efficiency"
            ]
        },
    ]
}


def _render_algorithm_group(group_name: str) -> None:
    for algorithm in ALGORITHM_CATEGORIES[group_name]:
        with st.container(border=True):
            st.markdown(f"#### {algorithm['name']}")
            st.markdown(algorithm['high_level'])
            with st.expander("Details & Example"):
                st.caption(
                    f"Algorithm: {algorithm['algorithm']} · "
                    f"Guarantee: {algorithm['guarantee']} · "
                    f"Complexity: {algorithm['complexity']}"
                )
                st.markdown("**Example Prompt**")
                try:
                    st.code(algorithm["full_example"], language=None, wrap_lines=True)
                except TypeError:
                    st.code(algorithm["full_example"], language=None)


def main():
    st.set_page_config(page_title="GraphBees Tutorials", page_icon="🐝", layout="wide")
    download_container, shutdown_disabled = render_sidebar()

    inject_shared_css()
    st.markdown(
        """<style>
        .block-container p, .block-container li, .block-container label { font-size: 13px !important; }
        .block-container h1 { font-size: 1.3rem !important; }
        .block-container h2 { font-size: 1.1rem !important; }
        .block-container h3 { font-size: 1rem !important; }
        .block-container h4 { font-size: 0.9rem !important; }
        </style>""",
        unsafe_allow_html=True,
    )
    maybe_shutdown(shutdown_disabled)

    st.title("Optimization Tutorials")
    _render_algorithm_group("Combinatorial Optimization")
    render_chat_download(download_container, st.session_state.get("messages", []))

if __name__ == "__main__":
    main()
