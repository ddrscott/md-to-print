"""Native macOS markdown viewer using WebKit with local server."""

import socket
import sys
import threading
from pathlib import Path

try:
    from AppKit import (
        NSApplication,
        NSApplicationActivationPolicyRegular,
        NSBackingStoreBuffered,
        NSWindow,
        NSWindowStyleMaskClosable,
        NSWindowStyleMaskMiniaturizable,
        NSWindowStyleMaskResizable,
        NSWindowStyleMaskTitled,
        NSMakeRect,
        NSScreen,
        NSObject,
    )
    from Foundation import NSURL
    from WebKit import WKWebView, WKWebViewConfiguration
    HAS_PYOBJC = True
except ImportError:
    HAS_PYOBJC = False


class AppDelegate(NSObject):
    """Application delegate to handle window close."""

    def applicationShouldTerminateAfterLastWindowClosed_(self, sender):
        return True


def show_native(md_path: Path) -> None:
    """Open a markdown file in a native macOS WebView window using local server."""
    if not HAS_PYOBJC:
        print("Native viewer requires pyobjc-framework-WebKit")
        print("Install with: uv add pyobjc-framework-WebKit")
        sys.exit(1)

    # Import server here to avoid circular imports
    from .server.app import create_app
    import uvicorn

    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]

    # Get the relative path for the URL
    root_path = md_path.parent
    file_name = md_path.name
    url = f"http://127.0.0.1:{port}/view/{file_name}?minimal=true"

    # Create the FastAPI app
    app = create_app(root_path)

    # Start server in background thread
    def run_server():
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        server = uvicorn.Server(config)
        server.run()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Give server time to start
    import time
    time.sleep(0.3)

    # Create application
    ns_app = NSApplication.sharedApplication()
    ns_app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    # Set delegate to quit on window close
    delegate = AppDelegate.alloc().init()
    ns_app.setDelegate_(delegate)

    # Calculate centered window position
    screen = NSScreen.mainScreen()
    screen_frame = screen.visibleFrame()

    window_width = 1200
    window_height = 800
    x = (screen_frame.size.width - window_width) / 2 + screen_frame.origin.x
    y = (screen_frame.size.height - window_height) / 2 + screen_frame.origin.y

    frame = NSMakeRect(x, y, window_width, window_height)

    # Create window
    style = (
        NSWindowStyleMaskTitled
        | NSWindowStyleMaskClosable
        | NSWindowStyleMaskMiniaturizable
        | NSWindowStyleMaskResizable
    )
    window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, style, NSBackingStoreBuffered, False
    )
    window.setTitle_(f"{md_path.stem} - md-to-print")
    window.setMinSize_(NSMakeRect(0, 0, 600, 400).size)

    # Create WebView
    config = WKWebViewConfiguration.alloc().init()
    webview = WKWebView.alloc().initWithFrame_configuration_(
        window.contentView().bounds(), config
    )
    webview.setAutoresizingMask_(0x12)  # NSViewWidthSizable | NSViewHeightSizable

    # Load URL from local server
    ns_url = NSURL.URLWithString_(url)
    from WebKit import NSURLRequest
    request = NSURLRequest.requestWithURL_(ns_url)
    webview.loadRequest_(request)

    # Show window
    window.setContentView_(webview)
    window.makeKeyAndOrderFront_(None)

    # Bring app to front
    ns_app.activateIgnoringOtherApps_(True)

    # Run event loop
    ns_app.run()
