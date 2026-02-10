"""Route handlers for the server."""

from .api import router as api_router
from .pages import router as pages_router
from .sse import router as sse_router

__all__ = ["api_router", "pages_router", "sse_router"]
