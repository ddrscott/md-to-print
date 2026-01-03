"""Command-line interface for md-to-print."""

import argparse
import sys
from pathlib import Path

from .converter import convert_file
from .watcher import watch_directory


def process_file(file_path: Path) -> None:
    """Process a single markdown file and print status."""
    try:
        output_path = convert_file(file_path)
        print(f"✓ {file_path.name} → {output_path.name}")
    except Exception as e:
        print(f"✗ {file_path.name}: {e}", file=sys.stderr)


def process_directory(directory: Path) -> int:
    """Process all markdown files in a directory.

    Returns:
        Number of files processed
    """
    md_files = list(directory.glob("**/*.md"))

    if not md_files:
        print(f"No markdown files found in {directory}")
        return 0

    for md_file in sorted(md_files):
        process_file(md_file)

    return len(md_files)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="md-to-print",
        description="Convert markdown files to printable 2-column PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  md-to-print document.md          Convert a single file
  md-to-print ./docs/              Convert all .md files in directory
  md-to-print --watch ./docs/      Watch directory for changes
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
        "-r", "--no-recursive",
        action="store_true",
        help="Don't process subdirectories (only applies to directories)",
    )

    args = parser.parse_args()
    path: Path = args.path.resolve()

    if not path.exists():
        print(f"Error: Path does not exist: {path}", file=sys.stderr)
        sys.exit(1)

    if path.is_file():
        if args.watch:
            # Watch the parent directory but only process this file
            print(f"Watching {path.name} for changes...")
            watch_directory(
                path.parent,
                lambda p: process_file(p) if p == path else None,
                recursive=False,
            )
        else:
            process_file(path)

    elif path.is_dir():
        if args.watch:
            # Initial conversion of all files
            count = process_directory(path)
            if count > 0:
                print(f"\nConverted {count} file(s)")
                print()

            # Then watch for changes
            watch_directory(
                path,
                process_file,
                recursive=not args.no_recursive,
            )
        else:
            count = process_directory(path)
            if count > 0:
                print(f"\nConverted {count} file(s)")

    else:
        print(f"Error: Invalid path: {path}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
