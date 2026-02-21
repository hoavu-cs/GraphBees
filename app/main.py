"""
Streamlit web app entry point for the network mining agent.
"""

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so `app.*` imports work when
# Streamlit runs this file as a standalone script.
_repo_root = str(Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import json

import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from app.agent import run
from app.julia_bridge.runner import init_julialg
from app.sidebar import maybe_shutdown, render_chat_download, render_sidebar
from app.styles import inject_shared_css

load_dotenv()


def _escape_dollars(text: str) -> str:
    """Escape $ signs so Streamlit doesn't render them as LaTeX."""
    return text.replace("$", "\\$")

ACCENT = "#5b5fc7"
PALETTE = ["#4f46e5", "#06b6d4", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6"]


@st.cache_resource
def _init_julia():
    """Initialize Julia runtime once across all Streamlit reruns."""
    init_julialg()


# Initialize Julia at import time so the first page load doesn't block.
_init_julia()


def _knapsack_figure(chart: dict) -> go.Figure:
    """Build a Plotly pie chart for knapsack capacity utilization."""
    colors = [
        "#a0a0a0" if (chart["hasRemaining"] and i == len(chart["labels"]) - 1)
        else PALETTE[i % len(PALETTE)]
        for i in range(len(chart["labels"]))
    ]
    fig = go.Figure(go.Pie(
        labels=chart["labels"],
        values=chart["sizes"],
        marker=dict(colors=colors),
        textinfo="label+percent",
    ))
    fig.update_layout(
        title="Knapsack: Capacity Utilization",
        margin=dict(t=40, b=20, l=20, r=20),
        height=350,
    )
    return fig


def _interval_figure(chart: dict) -> go.Figure:
    """Build a Plotly horizontal bar chart for interval scheduling."""
    jobs = chart["jobs"]
    selected = [j for j in jobs if j["selected"]]
    unselected = [j for j in jobs if not j["selected"]]
    ordered = list(reversed(selected + unselected))

    labels = []
    starts = []
    durations = []
    colors = []

    for j in ordered:
        labels.append(j["label"])
        starts.append(j["start"])
        durations.append(j["end"] - j["start"])
        if j["selected"]:
            idx = selected.index(j)
            colors.append(PALETTE[idx % len(PALETTE)])
        else:
            colors.append("#d0d0d0")

    fig = go.Figure(go.Bar(
        y=labels,
        x=durations,
        base=starts,
        orientation="h",
        marker=dict(color=colors),
    ))
    fig.update_layout(
        title="Selected (top) vs Not Selected (bottom)",
        xaxis_title="Time",
        margin=dict(t=40, b=40, l=120, r=20),
        height=max(len(labels) * 32 + 80, 200),
        showlegend=False,
    )
    return fig


def _bin_packing_figure(chart: dict) -> go.Figure:
    """Build a Plotly stacked bar chart for bin packing."""
    bins = chart["bins"]
    capacity = chart["capacity"]

    fig = go.Figure()

    # Find max items in any bin for layering
    max_items = max(len(b["sizes"]) for b in bins)

    for layer in range(max_items):
        sizes = []
        texts = []
        for b in bins:
            if layer < len(b["sizes"]):
                sizes.append(b["sizes"][layer])
                texts.append(f"Item {b['item_indices'][layer]} (size={b['sizes'][layer]})")
            else:
                sizes.append(0)
                texts.append("")

        fig.add_trace(go.Bar(
            x=[b["label"] for b in bins],
            y=sizes,
            text=texts,
            textposition="inside",
            marker=dict(color=PALETTE[layer % len(PALETTE)]),
            showlegend=False,
        ))

    # Add capacity line
    fig.add_hline(
        y=capacity,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Capacity = {capacity}",
        annotation_position="top right",
    )

    fig.update_layout(
        barmode="stack",
        title="Bin Packing: Items per Bin",
        yaxis_title="Fill Level",
        margin=dict(t=40, b=40, l=60, r=20),
        height=350,
    )
    return fig


def _chip(label: str, value: str, accent: str = "#5b5fc7") -> str:
    """Render a meta chip as an HTML span."""
    return (
        f'<span style="display:inline-flex; align-items:center; gap:4px; '
        f'background:#f0f0f8; color:{accent}; padding:2px 8px; '
        f'border-radius:20px; font-size:11px; font-weight:500; margin-right:4px;">'
        f'<span style="color:#8b8fa8; font-weight:400;">{label}</span> {value}'
        f'</span>'
    )


def _render_tool_card(log: dict):
    """Render a tool execution card."""
    is_error = bool(log.get("error"))
    border_color = "#d93025" if is_error else ACCENT
    name_color = "#d93025" if is_error else ACCENT
    bg_color = "rgba(217,48,37,0.03)" if is_error else "rgba(91,95,199,0.03)"

    st.markdown(
        f'<div style="border-left: 3px solid {border_color}; padding: 10px 14px; '
        f'background: {bg_color}; border-radius: 0 8px 8px 0; margin-bottom: 4px; '
        f'box-shadow: 0 1px 5px rgba(0,0,0,0.07); transition: box-shadow 0.15s ease;">'
        f'<div style="font-weight:600; color:{name_color}; font-size:14px; '
        f'letter-spacing:0.2px; margin-bottom:6px;">{log["solver"]}</div>',
        unsafe_allow_html=True,
    )

    chips = []
    if log.get("algorithm"):
        chips.append(_chip("Algorithm", log["algorithm"]))
    if log.get("guarantee"):
        chips.append(_chip("Guarantee", log["guarantee"]))
    if log.get("complexity"):
        chips.append(_chip("Complexity", log["complexity"]))
    if chips:
        st.markdown('<div style="margin-bottom:4px;">' + "".join(chips) + "</div>", unsafe_allow_html=True)

    if log.get("input_summary"):
        st.markdown(f"**Input:** {log['input_summary']}")

    if is_error:
        st.error(f"Error: {log['error']}")
    else:
        if log.get("result"):
            try:
                result_obj = json.loads(log["result"])
                result_str = json.dumps(result_obj, indent=2)
            except (json.JSONDecodeError, TypeError):
                result_str = str(log["result"])
            with st.expander("Result"):
                st.code(result_str, language="json")
        if log.get("elapsed_s") is not None:
            threads = log.get("julia_threads", "?")
            st.caption(f"Time: {log['elapsed_s']}s · Julia threads: {threads}")
        if log.get("chart"):
            chart = log["chart"]
            if chart["type"] == "knapsack":
                st.plotly_chart(_knapsack_figure(chart), use_container_width=True)
            elif chart["type"] == "interval":
                st.plotly_chart(_interval_figure(chart), use_container_width=True)
            elif chart["type"] == "bin_packing":
                st.plotly_chart(_bin_packing_figure(chart), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="GraphBees", page_icon="🐝", layout="centered")
    download_container, shutdown_disabled = render_sidebar()

    # Session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    inject_shared_css()
    # Global UI polish
    st.markdown(
        """<style>
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 1.5rem;
        }
        [data-testid="stSidebar"] .block-container {
            padding-top: 1rem;
        }
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] li,
        [data-testid="stSidebar"] a,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] [data-testid="stExpander"] summary p {
            font-size: 13px !important;
        }
        [data-testid="stSidebar"] div[data-testid="stButton"] > button {
            background-color: #d93025 !important;
            color: #ffffff !important;
            border: 1px solid #d93025 !important;
        }
        [data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
            background-color: #b3261e !important;
            border-color: #b3261e !important;
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] div[data-testid="stButton"] > button:disabled {
            background-color: #f2f2f2 !important;
            color: #9a9a9a !important;
            border-color: #e0e0e0 !important;
        }
        .stChatInput {
            border: 1px solid #d8d8e0 !important;
            border-radius: 12px !important;
            padding: 6px !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        }
        .stChatInput:focus-within {
            border-color: #5b5fc7 !important;
            box-shadow: 0 0 0 2px rgba(91,95,199,0.15);
        }
        div[data-testid="stCodeBlock"] pre {
            white-space: pre-wrap !important;
            word-break: break-word !important;
            overflow-wrap: anywhere !important;
        }
        /* Thin scrollbar */
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #c8c8d8; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #a0a0b8; }
        /* Expander polish */
        [data-testid="stExpander"] {
            border-radius: 10px !important;
            border-color: #eeeef2 !important;
        }
        /* Status alerts */
        [data-testid="stAlert"] {
            border-radius: 8px !important;
        }
        /* Chat message bubble containers */
        [data-testid="stChatMessage"] {
            border-radius: 10px;
        }
        </style>""",
        unsafe_allow_html=True,
    )

    maybe_shutdown(shutdown_disabled)

    # Header
    st.markdown(
        '<div style="display:flex; align-items:center; gap:12px; padding:4px 0 18px 0; '
        'border-bottom:1px solid #ebebf2; margin-bottom:20px;">'
        '<span style="font-size:30px; line-height:1;">🐝</span>'
        '<div>'
        '<h1 style="margin:0; font-size:19px; font-weight:700; letter-spacing:-0.3px;">GraphBees</h1>'
        '<p style="margin:0; font-size:12px; opacity:0.55;">Provably correct instead of probably correct</p>'
        '<p style="margin:0; font-size:12px; opacity:0.55;">Query → LLM → <b>Algorithmic Solvers</b> → Solution → LLM</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                # Render tool cards first, then the answer
                for log in msg.get("tool_logs", []):
                    _render_tool_card(log)
                if msg.get("content"):
                    st.markdown(_escape_dollars(msg["content"]))
            else:
                st.markdown(_escape_dollars(msg["content"]), unsafe_allow_html=True)

    # Chat input (or pending example prompt from Algorithms page)
    prompt = None
    if "example_prompt" in st.session_state:
        prompt = st.session_state.pop("example_prompt")
    elif user_prompt := st.chat_input("Describe your problem..."):
        prompt = user_prompt

    if prompt:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(_escape_dollars(prompt))

        # Run agent
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    result = run(prompt)
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Error: {e}",
                        "tool_logs": [],
                    })
                    return

            # Render tool cards
            for log in result.get("tool_logs", []):
                _render_tool_card(log)

            # Render answer
            answer = result.get("answer", "")
            if answer:
                st.markdown(_escape_dollars(answer))

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "tool_logs": result.get("tool_logs", []),
            })

    render_chat_download(download_container, st.session_state.messages)


if __name__ == "__main__":
    main()
