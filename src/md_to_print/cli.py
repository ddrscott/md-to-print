"""Command-line interface for md-to-print."""

import argparse
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.status import Status
from rich.table import Table
from rich.theme import Theme

from .converter import convert_file
from .watcher import watch_directory

# Custom theme matching brand colors
theme = Theme({
    "info": "dim",
    "success": "#3D7A4A",  # proceed green
    "warning": "#E85D00",  # signal orange
    "error": "#CC3333",    # stop red
    "filename": "bold",
    "muted": "#6B6B6B",
})

console = Console(theme=theme)


def print_pdf(pdf_path: Path) -> bool:
    """Send PDF to the default printer using lpr.

    Returns:
        True if print job was submitted successfully
    """
    try:
        subprocess.run(["lpr", str(pdf_path)], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        # lpr not available
        return False


def process_file(file_path: Path, force: bool = False, show_spinner: bool = True, debug: bool = False, print_after: bool = False) -> bool:
    """Process a single markdown file and print status.

    Returns:
        True if file was converted, False if skipped or errored
    """
    from .converter import needs_rebuild

    output_path = file_path.with_suffix(".pdf")

    # Check if rebuild needed before showing spinner
    if not force and not needs_rebuild(file_path, output_path):
        console.print(f"  [muted]·[/] [filename]{file_path.name}[/] [muted](up to date)[/]")
        return False

    try:
        if show_spinner:
            with console.status(f"[warning]Converting[/] [filename]{file_path.name}[/]...", spinner="dots") as status:
                result = convert_file(file_path, force=force, debug=debug)
        else:
            result = convert_file(file_path, force=force, debug=debug)

        if result is None:
            console.print(f"  [muted]·[/] [filename]{file_path.name}[/] [muted](up to date)[/]")
            return False

        status_parts = [f"  [success]✓[/] [filename]{file_path.name}[/] → [success]{result.name}[/]"]

        if print_after:
            if print_pdf(result):
                status_parts.append("[muted](sent to printer)[/]")
            else:
                status_parts.append("[error](print failed)[/]")

        console.print(" ".join(status_parts))
        return True

    except Exception as e:
        console.print(f"  [error]✗[/] [filename]{file_path.name}[/]: [error]{e}[/]")
        return False


def process_directory(directory: Path, force: bool = False, debug: bool = False, print_after: bool = False) -> tuple[int, int]:
    """Process all markdown files in a directory.

    Returns:
        Tuple of (converted_count, skipped_count)
    """
    md_files = list(directory.glob("**/*.md"))

    if not md_files:
        console.print(f"[muted]No markdown files found in {directory}[/]")
        return (0, 0)

    console.print(f"[info]Found {len(md_files)} markdown file(s)[/]\n")

    converted = 0
    skipped = 0

    for md_file in sorted(md_files):
        if process_file(md_file, force=force, debug=debug, print_after=print_after):
            converted += 1
        else:
            skipped += 1

    return (converted, skipped)


def print_summary(converted: int, skipped: int) -> None:
    """Print a summary table of results."""
    if converted == 0 and skipped == 0:
        return

    console.print()
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="bold")
    table.add_column(justify="right")

    if converted > 0:
        table.add_row("[success]Converted[/]", f"[success]{converted}[/]")
    if skipped > 0:
        table.add_row("[muted]Skipped (up to date)[/]", f"[muted]{skipped}[/]")

    console.print(table)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="md-to-print",
        description="Convert markdown files to printable 2-column PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  md-to-print document.md                Convert a single file
  md-to-print ./docs/                    Convert all .md files in directory
  md-to-print --watch ./docs/            Watch directory for changes
  md-to-print --force ./docs/            Force regenerate all PDFs
  md-to-print ./docs/ --serve            Start web viewer (auto-selects port)
  md-to-print ./docs/ --serve=8080       Start on specific port
  md-to-print . --serve=0.0.0.0:8080     Bind to all interfaces
  md-to-print . --serve --open           Start viewer and open browser
""",
    )

    parser.add_argument(
        "path",
        type=Path,
        help="Markdown file or directory to convert",
    )

    parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Watch for file changes and regenerate PDFs",
    )

    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force regeneration even if PDF is up to date",
    )

    parser.add_argument(
        "-r", "--no-recursive",
        action="store_true",
        help="Don't process subdirectories (only applies to directories)",
    )

    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Save intermediate HTML file alongside PDF for debugging",
    )

    parser.add_argument(
        "-p", "--print",
        action="store_true",
        dest="print_pdf",
        help="Send PDF to default printer after generating",
    )

    # Server mode arguments
    parser.add_argument(
        "-s", "--serve",
        nargs="?",
        const="",
        default=None,
        metavar="[HOST:]PORT",
        help="Start web server. Optional HOST:PORT (e.g., 0.0.0.0:8080) or just PORT. "
             "Defaults to localhost with auto-selected port.",
    )

    parser.add_argument(
        "-o", "--open",
        action="store_true",
        dest="open_browser",
        help="Open browser automatically when server starts",
    )

    args = parser.parse_args()
    path: Path = args.path.resolve()

    if not path.exists():
        console.print(f"[error]Error: Path does not exist: {path}[/]", file=sys.stderr)
        sys.exit(1)

    # Server mode
    if args.serve is not None:
        from .server import run_server
        import socket

        # For serve mode, if path is a file, serve its parent directory
        serve_path = path if path.is_dir() else path.parent

        # Parse host:port from --serve argument
        host = "127.0.0.1"
        port = 0  # 0 means auto-select

        if args.serve:
            if ":" in args.serve:
                # host:port format
                host, port_str = args.serve.rsplit(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    console.print(f"[error]Error: Invalid port '{port_str}'[/]", file=sys.stderr)
                    sys.exit(1)
            else:
                # Just port
                try:
                    port = int(args.serve)
                except ValueError:
                    console.print(f"[error]Error: Invalid port '{args.serve}'[/]", file=sys.stderr)
                    sys.exit(1)

        # Find a free port if not specified
        if port == 0:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, 0))
                port = s.getsockname()[1]

        run_server(
            root_path=serve_path,
            host=host,
            port=port,
            open_browser=args.open_browser,
        )
        return

    if path.is_file():
        if args.watch:
            console.print(f"[warning]Watching[/] [filename]{path.name}[/] for changes...\n")
            watch_directory(
                path.parent,
                lambda p: process_file(p, force=True, debug=args.debug, print_after=args.print_pdf) if p == path else None,
                recursive=False,
            )
        else:
            # Direct invocation always converts (no date checking)
            process_file(path, force=True, debug=args.debug, print_after=args.print_pdf)

    elif path.is_dir():
        if args.watch:
            # Initial conversion - check dates unless --force
            converted, skipped = process_directory(path, force=args.force, debug=args.debug, print_after=args.print_pdf)
            print_summary(converted, skipped)

            console.print(f"\n[warning]Watching[/] [filename]{path}[/] for changes...")
            console.print("[muted]Press Ctrl+C to stop.[/]\n")

            # Then watch for changes (always force on watch events)
            watch_directory(
                path,
                lambda p: process_file(p, force=True, debug=args.debug, print_after=args.print_pdf),
                recursive=not args.no_recursive,
            )
        else:
            # Direct invocation always converts (no date checking)
            converted, skipped = process_directory(path, force=True, debug=args.debug, print_after=args.print_pdf)
            print_summary(converted, skipped)

    else:
        console.print(f"[error]Error: Invalid path: {path}[/]", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
