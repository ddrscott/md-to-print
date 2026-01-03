# md-to-print

Markdown to printable 2-column PDF generator with file watching.

**Extremely opinionated** for aging eyes. Large fonts, high contrast, generous spacing. If you prefer different styling, edit `src/md_to_print/styles/print.css` to taste.

## Features

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

- [WeasyPrint](https://weasyprint.org/) - HTML/CSS to PDF engine
- [watchdog](https://github.com/gorakhargosh/watchdog) - File system monitoring
- [markdown](https://python-markdown.github.io/) - Markdown to HTML conversion
- [Pygments](https://pygments.org/) - Syntax highlighting
- [Rich](https://rich.readthedocs.io/) - Beautiful CLI output
- [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) (optional) - Diagram rendering
