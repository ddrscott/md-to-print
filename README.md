# md-to-print

Markdown to printable 2-column PDF generator with web viewer and file watching.

**Extremely opinionated** for aging eyes. Large fonts, high contrast, generous spacing. If you prefer different styling, edit `src/md_to_print/styles/print.css` to taste.

## Features

- **Web Viewer** - Browse and preview markdown files in your browser with live updates
- Converts markdown files to beautifully styled PDFs
- 2-column layout optimized for reading printed documents
- Page numbers, source filename, and print date in footer
- Document title in header (from first `<h1>`)
- Syntax highlighting for code blocks (custom color scheme)
- Mermaid diagram support (requires `mmdc` CLI)
- Smart keep-together rules (paragraphs, code blocks, lists don't break mid-element)
- Smart table handling (narrow tables stay in one column, wide tables span both)
- Watch mode for automatic regeneration on file changes
- Skips unchanged files (only regenerates when markdown is newer than PDF)
- US Letter paper size (8.5" x 11")

## Installation

```bash
# Clone and install
cd md-to-print
uv sync

# Optional: Install Mermaid CLI for diagram support
npm install -g @mermaid-js/mermaid-cli
```

## Usage

```bash
# Convert a single file
uv run md-to-print document.md

# Convert all .md files in a directory
uv run md-to-print ./docs/

# Watch mode - regenerate PDFs on file changes
uv run md-to-print --watch ./docs/

# Watch a single file
uv run md-to-print --watch document.md

# Force regeneration (ignore timestamps)
uv run md-to-print --force ./docs/
```

## Web Viewer (Server Mode)

Start a web server to browse and preview your markdown files with live updates:

```bash
# Start the viewer for current directory
uv run md-to-print --serve .

# Start with a specific directory and open browser automatically
uv run md-to-print --serve ~/Documents/notes --open

# Custom port
uv run md-to-print --serve . --port 3000

# All options
uv run md-to-print --serve ./docs --host 0.0.0.0 --port 8080 --open
```

**Web Viewer Features:**
- **Flat file list** with fuzzy search - all files at a glance, subdirectories shown as subtle labels
- **⌘K quick search** - instant filtering as you type
- **Full keyboard navigation** - Arrow keys to browse, Enter to select, Escape to clear
- **Horizontal column reading** - optimized for retention, scroll left/right through content
- **Adjustable reading controls** - column width, gap, and text alignment (persisted)
- **Expandable content** - click to expand tables, code blocks, images, and diagrams
- **Copy code blocks** - one-click copy to clipboard
- Preview markdown files with full syntax highlighting
- **Mermaid diagrams** - rendered client-side with full interactivity
- **ASCII diagrams** - svgbob/bob-wasm support for text-based diagrams
- Sort files by name or date (ascending/descending)
- Live updates when files change (no refresh needed)
- Dark mode support (persisted in browser)
- Collapsible sidebar (state persisted)
- Register as your default markdown viewer

**Keyboard Shortcuts:**
| Key | Action |
|-----|--------|
| `⌘K` / `Ctrl+K` | Focus search, open sidebar if closed |
| `↑` / `↓` | Navigate file list |
| `Enter` | Open selected file |
| `Escape` | Clear search / blur input |
| `←` / `→` | Scroll reading columns |
| `Space` | Scroll right one column |
| `Home` / `End` | Jump to start/end of document |

**Use as Default Markdown Viewer (macOS):**

1. Install globally: `uv tool install -U -e .`
2. Create a simple wrapper script that opens the viewer
3. Associate `.md` files with the wrapper in Finder

## Watch Mode Ideas

Watch mode shines when pointed at directories that receive markdown files automatically:

- **Downloads folder** - Any markdown files you download instantly become PDFs
- **Google Drive sync** - Shared markdown docs convert as they sync
- **Dropbox** - Collaborative markdown files auto-convert
- **Corporate shared drives** - Team documentation always print-ready
- **Obsidian vault** - Your notes ready for printing

```bash
# Watch your Downloads folder
uv run md-to-print --watch ~/Downloads

# Watch a synced Google Drive folder
uv run md-to-print --watch ~/Google\ Drive/Shared\ Docs

# Watch Dropbox
uv run md-to-print --watch ~/Dropbox/Notes
```

## Quick Start: Permanent Downloads Watcher (macOS)

Install globally and run automatically on login:

```bash
# Install as a global tool
uv tool install -U -e .

# Create LaunchAgent
cat > ~/Library/LaunchAgents/com.md-to-print.watch.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.md-to-print.watch</string>
    <key>ProgramArguments</key>
    <array>
        <string>$HOME/.local/bin/md-to-print</string>
        <string>--watch</string>
        <string>$HOME/Downloads</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/md-to-print.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/md-to-print.error.log</string>
</dict>
</plist>
EOF

# Replace $HOME with actual path (launchd doesn't expand variables)
sed -i '' "s|\$HOME|$HOME|g" ~/Library/LaunchAgents/com.md-to-print.watch.plist

# Start the service
launchctl load ~/Library/LaunchAgents/com.md-to-print.watch.plist

# Verify it's running
launchctl list | grep md-to-print
```

**Manage the service:**
```bash
# Stop
launchctl unload ~/Library/LaunchAgents/com.md-to-print.watch.plist

# Start
launchctl load ~/Library/LaunchAgents/com.md-to-print.watch.plist

# View logs
tail -f /tmp/md-to-print.log
```

## Output

PDFs are saved next to the source markdown files:
- `document.md` -> `document.pdf`
- `docs/guide.md` -> `docs/guide.pdf`

## Supported Markdown Features

- Headers (h1-h6) with `//` prefix styling
- Bold, italic, and inline code
- Code blocks with syntax highlighting (Python, JavaScript, etc.)
- Mermaid diagrams (flowcharts, sequence diagrams, state diagrams, etc.)
- ASCII diagrams using svgbob (use `ascii`, `bob`, or `svgbob` as language)
- Tables (auto-detected column span)
- Ordered and unordered lists (with nesting)
- Blockquotes with orange accent
- Links and images
- Horizontal rules

## Customization

The stylesheet lives at `src/md_to_print/styles/print.css`. Key things you might want to change:

- **Font sizes** - Adjust `html { font-size: 9.5pt; }` and heading sizes
- **Column count** - Change `columns: 2` to `columns: 1` for single-column
- **Paper size** - Change `size: letter` to `size: A4` or other
- **Colors** - Modify the CSS variables in `:root`
- **Margins** - Adjust the `@page { margin: ... }` rule

Mermaid diagram styling is in `src/md_to_print/styles/mermaid-config.json`.

## Dependencies

**PDF Generation:**
- [WeasyPrint](https://weasyprint.org/) - HTML/CSS to PDF engine
- [markdown](https://python-markdown.github.io/) - Markdown to HTML conversion
- [Pygments](https://pygments.org/) - Syntax highlighting
- [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) (optional) - Diagram rendering

**Web Viewer:**
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [uvicorn](https://www.uvicorn.org/) - ASGI server
- [Jinja2](https://jinja.palletsprojects.com/) - HTML templating
- [sse-starlette](https://github.com/sysid/sse-starlette) - Server-sent events

**Shared:**
- [watchdog](https://github.com/gorakhargosh/watchdog) - File system monitoring
- [Rich](https://rich.readthedocs.io/) - Beautiful CLI output
