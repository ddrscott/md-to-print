"""Server mode for browsing and previewing markdown files."""

import webbrowser
from pathlib import Path

import uvicorn
from rich.console import Console

console = Console()


def run_server(
    root_path: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = False,
) -> None:
    """Start the markdown viewer server."""
    from .app import create_app

    app = create_app(root_path)

    url = f"http://{host}:{port}"
    console.print(f"\n[green bold]md-to-print server[/] running at [link={url}]{url}[/link]")
    console.print(f"[dim]Serving files from:[/] {root_path.resolve()}")
    console.print("[dim]Press Ctrl+C to stop.[/]\n")

    if open_browser:
        webbrowser.open(url)

    uvicorn.run(app, host=host, port=port, log_level="warning")
