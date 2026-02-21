"""Shared CSS injected on every page."""

import streamlit as st

_SHARED_CSS = """
<style>
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
div[data-testid="stCodeBlock"] pre {
    white-space: pre-wrap !important;
    word-break: break-word !important;
    overflow-wrap: anywhere !important;
    border-radius: 10px !important;
}
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #c8c8d8; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #a0a0b8; }
[data-testid="stExpander"] {
    border-radius: 10px !important;
    border-color: #eeeef2 !important;
}
[data-testid="stAlert"] {
    border-radius: 8px !important;
}
</style>
"""


def inject_shared_css() -> None:
    """Inject shared CSS into the current Streamlit page."""
    st.markdown(_SHARED_CSS, unsafe_allow_html=True)