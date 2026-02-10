# Part 1: Introduction

This is the first part of the document. It should appear on page 1 along with all content that follows until we reach Part 2.

## Overview

The md-to-print tool converts markdown files into beautifully formatted, two-column PDFs designed for printing. The tool uses WeasyPrint for PDF generation and includes custom styling based on the Scott Pierce brand identity.

### Key Features

- Two-column layout for efficient use of page space
- Custom syntax highlighting with Pygments
- Mermaid diagram support
- Automatic table of contents
- Page numbers and document metadata in footers

## Getting Started

To use the tool, simply run:

```bash
md-to-print document.md
```

This will generate a `document.pdf` file in the same directory.

### Installation

Install the tool using pip:

```bash
pip install md-to-print
```

Or with uv:

```bash
uv add md-to-print
```

## Configuration Options

The tool supports several command-line flags:

| Flag | Description |
|------|-------------|
| `-w, --watch` | Watch for file changes |
| `-f, --force` | Force regeneration |
| `-d, --debug` | Save intermediate HTML |

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

---

# Part 2: Advanced Topics

This is Part 2. It MUST start on page 2, and this paragraph should appear immediately after the heading on the same page. The H1 heading should never be orphaned at the bottom of a page without at least some content following it.

## Code Highlighting

The tool uses Pygments for syntax highlighting with a custom theme:

```python
def convert_file(input_path: Path, force: bool = False) -> Path | None:
    """Convert a markdown file to PDF.

    Args:
        input_path: Path to the markdown file
        force: If True, regenerate even if PDF is up to date

    Returns:
        Path to the generated PDF file
    """
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    md_content = input_path.read_text(encoding="utf-8")
    html_content = markdown_to_html(md_content)
    html_to_pdf(html_content, output_path)

    return output_path
```

## Tables

Tables automatically span both columns when they have more than 3 columns:

| ID | Name | Category | Status | Priority | Description |
|----|------|----------|--------|----------|-------------|
| 1 | Alpha | Core | Active | High | Primary component |
| 2 | Beta | Plugin | Pending | Medium | Extension framework |
| 3 | Gamma | API | Active | High | External interface |
| 4 | Delta | Core | Deprecated | Low | Legacy support |
| 5 | Epsilon | Background | Active | Medium | Async processing |

## Conclusion

The md-to-print tool provides a simple way to create professional-looking printed documents from markdown source files. The two-column layout maximizes content density while maintaining readability.

---

# Part 3: Appendix

This is Part 3. Like Part 2, it should start on a new page with the heading and content together.

## Additional Resources

- WeasyPrint documentation
- Pygments style guide
- Markdown syntax reference

## Changelog

### Version 1.0.0

- Initial release
- Two-column PDF generation
- Syntax highlighting
- Watch mode for development
