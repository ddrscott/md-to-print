"""FastAPI application factory for the markdown viewer."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes import api_router, pages_router, sse_router
from .services.file_watcher import AsyncFileWatcher


def create_app(root_path: Path) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        root_path: Root directory for serving markdown files

    Returns:
        Configured FastAPI application
    """
    root_path = root_path.resolve()

    # Create file watcher
    file_watcher = AsyncFileWatcher(root_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Handle startup and shutdown events."""
        # Start file watcher
        loop = asyncio.get_event_loop()
        file_watcher.start(loop)
        yield
        # Stop file watcher
        file_watcher.stop()

    app = FastAPI(
        title="md-to-print Viewer",
        description="Browse and preview markdown files",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Store root path and file watcher in app state
    app.state.root_path = root_path
    app.state.file_watcher = file_watcher

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Include routers
    app.include_router(api_router)
    app.include_router(sse_router)
    app.include_router(pages_router)

    return app
