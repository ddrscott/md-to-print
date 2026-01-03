"""Markdown to PDF converter using WeasyPrint."""

import re
from pathlib import Path

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension
from pygments.formatters import HtmlFormatter
from weasyprint import HTML, CSS

# Tables with this many columns or fewer stay in one column
NARROW_TABLE_THRESHOLD = 3


def get_stylesheet() -> str:
    """Load the print stylesheet from package resources."""
    styles_path = Path(__file__).parent / "styles" / "print.css"
    return styles_path.read_text()


def get_pygments_css() -> str:
    """Generate Pygments CSS for syntax highlighting."""
    formatter = HtmlFormatter(style="default")
    return formatter.get_style_defs(".codehilite")


def _count_table_columns(table_html: str) -> int:
    """Count columns in a table by examining the first row."""
    # Find first row (thead tr or tbody tr)
    row_match = re.search(r"<tr[^>]*>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)
    if not row_match:
        return 0
    row = row_match.group(1)
    # Count th or td elements
    cells = re.findall(r"<t[hd][^>]*>", row, re.IGNORECASE)
    return len(cells)


def _classify_tables(html: str) -> str:
    """Add 'narrow' class to tables with few columns."""
    def replace_table(match: re.Match) -> str:
        table_html = match.group(0)
        col_count = _count_table_columns(table_html)

        if col_count <= NARROW_TABLE_THRESHOLD:
            # Add narrow class
            if 'class="' in table_html:
                return table_html.replace('class="', 'class="narrow ', 1)
            else:
                return table_html.replace("<table", '<table class="narrow"', 1)
        return table_html

    return re.sub(r"<table[^>]*>.*?</table>", replace_table, html, flags=re.DOTALL | re.IGNORECASE)


def markdown_to_html(md_content: str, title: str = "Document") -> str:
    """Convert markdown content to a full HTML document.

    Args:
        md_content: Raw markdown text
        title: Document title for the HTML head

    Returns:
        Complete HTML document as string
    """
    md = markdown.Markdown(
        extensions=[
            FencedCodeExtension(),
            CodeHiliteExtension(css_class="codehilite", guess_lang=False),
            TableExtension(),
            TocExtension(toc_depth=3),
            "smarty",
        ]
    )

    html_body = md.convert(md_content)
    html_body = _classify_tables(html_body)
    pygments_css = get_pygments_css()

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
{pygments_css}
    </style>
</head>
<body>
    <article>
{html_body}
    </article>
</body>
</html>"""

    return html_doc


def html_to_pdf(html_content: str, output_path: Path) -> None:
    """Convert HTML to PDF using WeasyPrint.

    Args:
        html_content: Complete HTML document
        output_path: Path to write the PDF file
    """
    stylesheet = get_stylesheet()
    html_doc = HTML(string=html_content)
    css = CSS(string=stylesheet)
    html_doc.write_pdf(output_path, stylesheets=[css])


def convert_file(input_path: Path) -> Path:
    """Convert a markdown file to PDF.

    Args:
        input_path: Path to the markdown file

    Returns:
        Path to the generated PDF file
    """
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    if not input_path.suffix.lower() == ".md":
        raise ValueError(f"Not a markdown file: {input_path}")

    md_content = input_path.read_text(encoding="utf-8")
    title = input_path.stem.replace("-", " ").replace("_", " ").title()

    html_content = markdown_to_html(md_content, title)

    output_path = input_path.with_suffix(".pdf")
    html_to_pdf(html_content, output_path)

    return output_path
