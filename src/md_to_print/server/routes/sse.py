"""Server-Sent Events endpoint for live file updates."""

import asyncio
import json

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api/v1")


async def event_generator(request: Request):
    """Generate SSE events for connected clients."""
    watcher = request.app.state.file_watcher
    queue = watcher.subscribe()

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                # Wait for events with timeout (for keepalive)
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield {
                    "event": event["type"],
                    "data": json.dumps(event),
                    "retry": 5000,
                }
            except asyncio.TimeoutError:
                # Send keepalive comment
                yield {"comment": "keepalive"}
    finally:
        watcher.unsubscribe(queue)


@router.get("/events")
async def sse_endpoint(request: Request):
    """SSE endpoint for file change notifications."""
    return EventSourceResponse(event_generator(request))
