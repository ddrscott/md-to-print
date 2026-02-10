/**
 * SSE Event Handler for live file updates
 * Dispatches custom events that HTMX listens to
 */

class FileWatcher {
    constructor() {
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.eventSource = null;

        // Don't connect if htmx-ext-sse is handling it
        // The sse extension handles connection automatically
        console.log('[md-to-print] SSE handler initialized');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new FileWatcher();

    // Log SSE events for debugging
    document.body.addEventListener('htmx:sseMessage', (e) => {
        console.log('[md-to-print] SSE message:', e.detail);
    });

    // Add visual feedback for HTMX requests
    document.body.addEventListener('htmx:beforeRequest', () => {
        document.body.classList.add('htmx-loading');
    });

    document.body.addEventListener('htmx:afterRequest', () => {
        document.body.classList.remove('htmx-loading');
    });
});

// Notify user of file changes with subtle indicator
function showUpdateNotification(message) {
    // Could add a toast notification here if desired
    console.log('[md-to-print]', message);
}
