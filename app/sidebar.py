"""Shared sidebar and app panel helpers."""

import os
import textwrap
import threading
import time

import streamlit as st

from app.config import has_api_config


_THIN_HR = '<hr style="border:none; border-top:1px solid #ebebf2; margin:10px 0;">'


def _shutdown_server() -> None:
    """Terminate the Streamlit process."""
    os._exit(0)


def _shutdown_disabled_on_cloud() -> bool:
    """Disable local process shutdown controls on managed cloud platforms."""
    shutdown_flag = str(os.environ.get("GRAPHBEES_ALLOW_SHUTDOWN", "")).strip().lower()
    if shutdown_flag in {"0", "false", "no", "off"}:
        return True
    if shutdown_flag in {"1", "true", "yes", "on"}:
        return False
    return any(
        os.environ.get(key)
        for key in (
            "RENDER",
            "RENDER_SERVICE_ID",
            "STREAMLIT_SHARING_MODE",
            "STREAMLIT_CLOUD",
        )
    )


def _shutdown_button_hidden() -> bool:
    """Hide the shutdown button when explicitly disabled via env var."""
    shutdown_flag = str(os.environ.get("GRAPHBEES_ALLOW_SHUTDOWN", "")).strip().lower()
    return shutdown_flag in {"0", "false", "no", "off"}


def _chat_transcript_lines(messages: list[dict], wrap_width: int = 100) -> list[str]:
    """Build transcript lines from chat messages."""
    lines: list[str] = [
        "GraphBees Chat Export",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for msg in messages:
        role = str(msg.get("role", "assistant")).upper()
        lines.append(f"{role}:")

        content = str(msg.get("content", "") or "").strip()
        if content:
            for paragraph in content.splitlines() or [""]:
                lines.extend(textwrap.wrap(paragraph, width=wrap_width) or [""])

        if role == "ASSISTANT":
            for log in msg.get("tool_logs", []):
                solver = str(log.get("solver", "tool"))
                if log.get("error"):
                    lines.extend(textwrap.wrap(f"[Tool: {solver}] Error: {log['error']}", width=wrap_width))
                elif log.get("result"):
                    preview = str(log["result"])
                    if len(preview) > 300:
                        preview = preview[:300] + "..."
                    lines.extend(textwrap.wrap(f"[Tool: {solver}] Result: {preview}", width=wrap_width))

        lines.append("")

    return lines


def _chat_to_txt_bytes(messages: list[dict]) -> bytes:
    """Build a UTF-8 TXT transcript from chat messages."""
    text = "\n".join(_chat_transcript_lines(messages, wrap_width=120))
    return text.encode("utf-8")


def render_sidebar() -> tuple[object, bool]:
    """Render the shared sidebar panel and return download container + shutdown state."""
    shutdown_disabled = _shutdown_disabled_on_cloud()
    shutdown_hidden = _shutdown_button_hidden()

    with st.sidebar:

        st.markdown("GraphBees 🐝 is an optimization assistant equipped with algorithmic solvers.")
        st.markdown("---")
        download_container = st.container()

        with st.expander("What's interesting?"):
            st.markdown("Think of this app as your optimization sidekick: it understands your scenario, then hands it to **provably correct** algorithms for the heavy lifting. LLMs are only used for interpretation, not for guessing results.")
        
        with st.expander("Usage & Deployment Notes"):
            st.markdown(
                """
                - For the online version, LLM API costs are on me. Please use responsibly.
                - For strong and multithreaded performance, consider [running locally](https://github.com/hoavu-cs/GraphBees#running-locally). 
                You will need your own API key from an LLM provider such as [OpenAI](https://platform.openai.com/account/api-keys), [DeepSeek](https://api-docs.deepseek.com/), etc or a local LLM.
                - If you want to scale up or customize for your team or company, especially with really large datasets and graph data, 
                reach out to us at [graphbees.qa@gmail.com](mailto:graphbees.qa@gmail.com).
                - [Report Issues](https://github.com/hoavu-cs/GraphBees/issues).
                """
            )

        if not shutdown_hidden:
            exit_app = st.button("Shut Down", disabled=shutdown_disabled, use_container_width=True)
            if shutdown_disabled:
                st.caption("Disabled on cloud deployments")
            elif exit_app:
                st.session_state.shutdown_requested = True
                st.rerun()

        st.markdown(_THIN_HR, unsafe_allow_html=True)
        st.markdown("**API Status**")
        if has_api_config():
            st.success("Configured")
        else:
            st.warning("LLM_API or LLM_URL missing")

    return download_container, shutdown_disabled


def render_chat_download(container: object, messages: list[dict]) -> None:
    """Render chat transcript download button into the provided sidebar container."""
    container.download_button(
        "Download Chat .TXT",
        data=_chat_to_txt_bytes(messages),
        file_name="graphbees_chat.txt",
        mime="text/plain; charset=utf-8",
        use_container_width=True,
    )


def maybe_shutdown(shutdown_disabled: bool) -> None:
    """Process deferred shutdown if requested by the sidebar button."""
    if st.session_state.get("shutdown_requested") and not shutdown_disabled:
        if not st.session_state.get("shutdown_scheduled"):
            st.session_state.shutdown_scheduled = True
            threading.Timer(1.0, _shutdown_server).start()

        st.info("Shutting down GraphBees...")
        time.sleep(0.2)
        st.stop()
