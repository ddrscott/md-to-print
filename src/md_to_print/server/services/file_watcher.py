"""Async file watcher for SSE live updates."""

import asyncio
import json
import threading
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ..models import FileType
from .file_browser import get_file_type, IMAGE_EXTENSIONS


class AsyncFileWatcher:
    """Async wrapper for file watching with SSE integration."""

    def __init__(self, root_path: Path):
        self.root_path = root_path.resolve()
        self.observer = Observer()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: set[asyncio.Queue] = set()
        self._lock = threading.Lock()

    def subscribe(self) -> asyncio.Queue:
        """Create a new event queue for a subscriber."""
        queue: asyncio.Queue = asyncio.Queue()
        with self._lock:
            self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber's event queue."""
        with self._lock:
            self._subscribers.discard(queue)

    def broadcast(self, event: dict) -> None:
        """Broadcast event to all subscribers."""
        if not self._loop:
            return

        with self._lock:
            for queue in self._subscribers:
                try:
                    self._loop.call_soon_threadsafe(
                        queue.put_nowait, event
                    )
                except asyncio.QueueFull:
                    pass

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Start watching for file changes."""
        self._loop = loop
        handler = SSEEventHandler(self)
        self.observer.schedule(handler, str(self.root_path), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        """Stop watching."""
        self.observer.stop()
        self.observer.join()


class SSEEventHandler(FileSystemEventHandler):
    """File system event handler that broadcasts to SSE subscribers."""

    SUPPORTED_EXTENSIONS = {".md", *IMAGE_EXTENSIONS}

    def __init__(self, watcher: AsyncFileWatcher):
        self.watcher = watcher
        self._debounce_timers: dict[str, threading.Timer] = {}
        self._debounce_lock = threading.Lock()

    def _is_relevant(self, path: str) -> bool:
        """Check if the path should trigger an event."""
        p = Path(path)
        # Skip hidden files
        if p.name.startswith("."):
            return False
        return p.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def _get_file_type_str(self, path: Path) -> str:
        """Get file type as string for event."""
        file_type = get_file_type(path)
        return file_type.value

    def _emit(self, event_type: str, path: str) -> None:
        """Emit an event with debouncing."""
        if not self._is_relevant(path):
            return

        with self._debounce_lock:
            # Cancel existing timer for this path
            if path in self._debounce_timers:
                self._debounce_timers[path].cancel()

            # Set new timer with debounce delay
            timer = threading.Timer(
                0.3,  # 300ms debounce
                self._do_emit,
                args=(event_type, path),
            )
            self._debounce_timers[path] = timer
            timer.start()

    def _do_emit(self, event_type: str, path: str) -> None:
        """Actually emit the event after debounce delay."""
        p = Path(path)

        try:
            relative_path = str(p.relative_to(self.watcher.root_path))
            parent_path = str(p.parent.relative_to(self.watcher.root_path))
            if parent_path == ".":
                parent_path = ""
        except ValueError:
            return

        event = {
            "type": f"file_{event_type}",
            "path": relative_path,
            "fileType": self._get_file_type_str(p),
            "timestamp": datetime.now().isoformat(),
            "affectedFolder": parent_path,
        }
        self.watcher.broadcast(event)

        # Clean up timer reference
        with self._debounce_lock:
            self._debounce_timers.pop(path, None)

    def on_created(self, event):
        if not event.is_directory:
            self._emit("created", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._emit("modified", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._emit("deleted", event.src_path)
