"""Allow running the app with `python -m app`."""

import os
import sys
from streamlit.web.cli import main as st_main

if __name__ == "__main__":
    port = os.environ.get("PORT", "8501")
    sys.argv = [
        "streamlit", "run", "app/main.py",
        f"--server.port={port}",
        "--server.address=127.0.0.1",
        "--server.fileWatcherType=none",
    ]
    st_main()
