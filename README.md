# md-to-print

Markdown to printable 2-column PDF generator with file watching.

## Features

- Converts markdown files to beautifully styled PDFs
- 2-column layout optimized for reading printed documents
- Page numbers in footer
- Document title in header (from first `<h1>`)
- Syntax highlighting for code blocks
- Smart keep-together rules (paragraphs, code blocks, lists don't break mid-element)
- Watch mode for automatic regeneration on file changes
- US Letter paper size (8.5" x 11")

## Installation

```bash
# Clone and install
cd md-to-print
uv sync
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
```

## Output

PDFs are saved next to the source markdown files:
- `document.md` → `document.pdf`
- `docs/guide.md` → `docs/guide.pdf`

## Supported Markdown Features

- Headers (h1-h6)
- Bold, italic, and inline code
- Code blocks with syntax highlighting (Python, JavaScript, etc.)
- Tables
- Ordered and unordered lists (with nesting)
- Blockquotes
- Links and images
- Horizontal rules

## Dependencies

- [WeasyPrint](https://weasyprint.org/) - HTML/CSS to PDF engine
- [watchdog](https://github.com/gorakhargosh/watchdog) - File system monitoring
- [markdown](https://python-markdown.github.io/) - Markdown to HTML conversion
- [Pygments](https://pygments.org/) - Syntax highlighting
