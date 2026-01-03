"""File watcher for automatic markdown to PDF conversion."""

import sys
import time
from pathlib import Path
from threading import Timer
from typing import Callable

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class MarkdownHandler(FileSystemEventHandler):
    """Handle markdown file changes with debouncing."""

    def __init__(self, callback: Callable[[Path], None], debounce_seconds: float = 0.5):
        """Initialize the handler.

        Args:
            callback: Function to call when a markdown file changes
            debounce_seconds: Time to wait before triggering callback (for rapid saves)
        """
        super().__init__()
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._pending_timers: dict[str, Timer] = {}

    def _is_markdown_file(self, path: str) -> bool:
        """Check if the path is a markdown file."""
        return path.lower().endswith(".md")

    def _schedule_callback(self, path: Path) -> None:
        """Schedule a callback with debouncing."""
        path_str = str(path)

        # Cancel any pending timer for this file
        if path_str in self._pending_timers:
            self._pending_timers[path_str].cancel()

        # Schedule new callback
        timer = Timer(self.debounce_seconds, self._execute_callback, args=[path])
        self._pending_timers[path_str] = timer
        timer.start()

    def _execute_callback(self, path: Path) -> None:
        """Execute the callback and clean up timer."""
        path_str = str(path)
        if path_str in self._pending_timers:
            del self._pending_timers[path_str]

        try:
            self.callback(path)
        except Exception as e:
            print(f"Error processing {path}: {e}", file=sys.stderr)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if not event.is_directory and self._is_markdown_file(event.src_path):
            self._schedule_callback(Path(event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory and self._is_markdown_file(event.src_path):
            self._schedule_callback(Path(event.src_path))


def watch_directory(
    directory: Path,
    callback: Callable[[Path], None],
    recursive: bool = True,
) -> None:
    """Watch a directory for markdown file changes.

    Args:
        directory: Directory to watch
        callback: Function to call when a markdown file changes
        recursive: Whether to watch subdirectories
    """
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    handler = MarkdownHandler(callback)
    observer = Observer()
    observer.schedule(handler, str(directory), recursive=recursive)

    print(f"Watching {directory} for markdown changes...")
    print("Press Ctrl+C to stop.")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()

    observer.join()
