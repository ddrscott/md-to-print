"""Standalone viewer - starts a temporary server for a single file."""

import socket
import threading
import time
import webbrowser
from pathlib import Path


def show_markdown(md_path: Path) -> None:
    """Open a markdown file using a temporary server instance."""
    from .server import run_server

    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]

    # Get the relative path for the URL
    root_path = md_path.parent
    file_name = md_path.name

    # URL to open
    url = f"http://127.0.0.1:{port}/view/{file_name}?minimal=true"

    # Open browser after a short delay
    def open_browser():
        time.sleep(0.5)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    # Start server (this blocks)
    print(f"Starting viewer at {url}")
    print("Press Ctrl+C to stop")
    run_server(
        root_path=root_path,
        host="127.0.0.1",
        port=port,
        open_browser=False,  # We handle this ourselves
    )
