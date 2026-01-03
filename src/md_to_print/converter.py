"""Markdown to PDF converter using WeasyPrint."""

import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension
from pygments.formatters import HtmlFormatter
from pygments.style import Style
from pygments.token import (
    Comment, Error, Generic, Keyword, Literal, Name, Number,
    Operator, Punctuation, String, Token, Whitespace
)
from weasyprint import HTML, CSS

# Tables with this many columns or fewer stay in one column
NARROW_TABLE_THRESHOLD = 3


class ScottPierceStyle(Style):
    """Custom Pygments style matching askscottpierce brand.

    Uses Clarity Stack colors with Signal Orange accent.
    """
    name = "scottpierce"

    background_color = "#F7F6F3"  # paper-dark
    highlight_color = "rgba(232, 93, 0, 0.1)"  # orange-bg

    styles = {
        Token:                  "#2C2C2C",      # ink
        Whitespace:             "#2C2C2C",

        Comment:                "italic #6B6B6B",  # ink-muted
        Comment.Preproc:        "noitalic #E85D00",  # orange
        Comment.Special:        "bold italic #6B6B6B",

        Keyword:                "bold #E85D00",  # orange - keywords pop
        Keyword.Constant:       "#E85D00",
        Keyword.Declaration:    "bold #E85D00",
        Keyword.Namespace:      "bold #E85D00",
        Keyword.Type:           "#3D7A4A",  # proceed green

        Operator:               "#2C2C2C",
        Operator.Word:          "bold #E85D00",

        Punctuation:            "#6B6B6B",  # ink-muted

        Name:                   "#2C2C2C",
        Name.Attribute:         "#3D7A4A",  # proceed green
        Name.Builtin:           "#E85D00",
        Name.Builtin.Pseudo:    "#6B6B6B",
        Name.Class:             "bold #2C2C2C",
        Name.Constant:          "#E85D00",
        Name.Decorator:         "#D4722A",  # orange-hover
        Name.Entity:            "#E85D00",
        Name.Exception:         "bold #CC3333",  # stop red
        Name.Function:          "#2C2C2C",
        Name.Function.Magic:    "#E85D00",
        Name.Label:             "#E85D00",
        Name.Namespace:         "#2C2C2C",
        Name.Tag:               "bold #E85D00",
        Name.Variable:          "#2C2C2C",
        Name.Variable.Class:    "#2C2C2C",
        Name.Variable.Global:   "#E85D00",
        Name.Variable.Instance: "#2C2C2C",
        Name.Variable.Magic:    "#E85D00",

        String:                 "#3D7A4A",  # proceed green for strings
        String.Affix:           "#E85D00",
        String.Backtick:        "#3D7A4A",
        String.Doc:             "italic #6B6B6B",
        String.Escape:          "#D4722A",
        String.Interpol:        "#E85D00",
        String.Regex:           "#D4722A",
        String.Symbol:          "#3D7A4A",

        Number:                 "#E85D00",  # orange for numbers

        Generic.Deleted:        "#CC3333",
        Generic.Emph:           "italic",
        Generic.Error:          "#CC3333",
        Generic.Heading:        "bold #2C2C2C",
        Generic.Inserted:       "#3D7A4A",
        Generic.Output:         "#6B6B6B",
        Generic.Prompt:         "bold #E85D00",
        Generic.Strong:         "bold",
        Generic.Subheading:     "bold #6B6B6B",
        Generic.Traceback:      "#CC3333",

        Error:                  "bg:#CC3333 #FFFEF9",
    }


def get_stylesheet() -> str:
    """Load the print stylesheet from package resources."""
    styles_path = Path(__file__).parent / "styles" / "print.css"
    return styles_path.read_text()


def get_pygments_css() -> str:
    """Generate Pygments CSS with custom Scott Pierce style."""
    formatter = HtmlFormatter(style=ScottPierceStyle)
    return formatter.get_style_defs(".codehilite")


def _count_table_columns(table_html: str) -> int:
    """Count columns in a table by examining the first row."""
    row_match = re.search(r"<tr[^>]*>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)
    if not row_match:
        return 0
    row = row_match.group(1)
    cells = re.findall(r"<t[hd][^>]*>", row, re.IGNORECASE)
    return len(cells)


def _classify_tables(html: str) -> str:
    """Add 'narrow' class to tables with few columns."""
    def replace_table(match: re.Match) -> str:
        table_html = match.group(0)
        col_count = _count_table_columns(table_html)

        if col_count <= NARROW_TABLE_THRESHOLD:
            if 'class="' in table_html:
                return table_html.replace('class="', 'class="narrow ', 1)
            else:
                return table_html.replace("<table", '<table class="narrow"', 1)
        return table_html

    return re.sub(r"<table[^>]*>.*?</table>", replace_table, html, flags=re.DOTALL | re.IGNORECASE)


def _has_mermaid_cli() -> bool:
    """Check if mermaid-cli (mmdc) is available."""
    return shutil.which("mmdc") is not None


def _get_mermaid_config_path() -> Path:
    """Get path to the Mermaid config file."""
    return Path(__file__).parent / "styles" / "mermaid-config.json"


def _render_mermaid(code: str) -> str:
    """Render Mermaid diagram to inline SVG.

    Returns SVG string on success, or a styled error message on failure.
    """
    if not _has_mermaid_cli():
        return f'''<div class="mermaid-error">
            <strong>Mermaid CLI not installed.</strong><br>
            Install with: <code>npm install -g @mermaid-js/mermaid-cli</code>
            <pre>{code}</pre>
        </div>'''

    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as f:
            f.write(code)
            input_path = f.name

        output_path = input_path.replace('.mmd', '.png')
        config_path = _get_mermaid_config_path()

        # Run mmdc with custom config - use PNG for reliable text rendering
        # SVG has issues with foreignObject not rendering in WeasyPrint
        cmd = [
            "mmdc",
            "-i", input_path,
            "-o", output_path,
            "-b", "transparent",
            "-s", "3",  # 3x scale for crisp print text
            "-w", "500",  # Constrain width so text stays readable
        ]

        # Use custom config if it exists
        if config_path.exists():
            cmd.extend(["-c", str(config_path)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return f'''<div class="mermaid-error">
                <strong>Mermaid rendering failed:</strong>
                <pre>{result.stderr}</pre>
                <pre>{code}</pre>
            </div>'''

        # Read PNG and encode as base64 data URI
        import base64
        png_data = Path(output_path).read_bytes()
        b64_data = base64.b64encode(png_data).decode('ascii')

        # Clean up temp files
        Path(input_path).unlink(missing_ok=True)
        Path(output_path).unlink(missing_ok=True)

        return f'<div class="mermaid-diagram"><img src="data:image/png;base64,{b64_data}" alt="Mermaid diagram" /></div>'

    except subprocess.TimeoutExpired:
        return f'''<div class="mermaid-error">
            <strong>Mermaid rendering timed out.</strong>
            <pre>{code}</pre>
        </div>'''
    except Exception as e:
        return f'''<div class="mermaid-error">
            <strong>Mermaid error: {e}</strong>
            <pre>{code}</pre>
        </div>'''


def _process_mermaid_blocks(md_content: str) -> str:
    """Extract and render mermaid code blocks before markdown processing."""
    mermaid_pattern = re.compile(
        r'```mermaid\s*\n(.*?)\n```',
        re.DOTALL | re.IGNORECASE
    )

    def replace_mermaid(match: re.Match) -> str:
        code = match.group(1).strip()
        svg = _render_mermaid(code)
        # Use HTML comment markers to protect from markdown processing
        return f'\n\n<div class="mermaid-wrapper">{svg}</div>\n\n'

    return mermaid_pattern.sub(replace_mermaid, md_content)


def markdown_to_html(
    md_content: str,
    title: str = "Document",
    source_path: str | None = None,
    generated_at: str | None = None,
) -> str:
    """Convert markdown content to a full HTML document.

    Args:
        md_content: Raw markdown text
        title: Document title for the HTML head
        source_path: Absolute path to source file (for footer)
        generated_at: Generation timestamp (for footer)

    Returns:
        Complete HTML document as string
    """
    # Process mermaid blocks first (before markdown conversion)
    md_content = _process_mermaid_blocks(md_content)

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

    # Metadata for running footer
    source_path = source_path or ""
    generated_at = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")

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
    <div class="doc-meta">
        <span class="source-path">{source_path}</span>
        <span class="generated-at">{generated_at}</span>
    </div>
    <article>
{html_body}
    </article>
</body>
</html>"""

    return html_doc


def html_to_pdf(
    html_content: str,
    output_path: Path,
    source_path: str = "",
    generated_at: str = "",
) -> None:
    """Convert HTML to PDF using WeasyPrint.

    Args:
        html_content: Complete HTML document
        output_path: Path to write the PDF file
        source_path: Source file path for footer
        generated_at: Generation timestamp for footer
    """
    stylesheet = get_stylesheet()

    # Inject footer values directly into CSS (string-set is unreliable)
    footer_css = f"""
    @page {{
        @bottom-left {{
            content: "{source_path}";
        }}
        @bottom-right {{
            content: "Printed {generated_at}";
        }}
    }}
    """

    html_doc = HTML(string=html_content)
    css = CSS(string=stylesheet)
    footer_overrides = CSS(string=footer_css)
    html_doc.write_pdf(output_path, stylesheets=[css, footer_overrides])


def needs_rebuild(input_path: Path, output_path: Path) -> bool:
    """Check if PDF needs to be regenerated.

    Returns True if:
    - Output doesn't exist
    - Input is newer than output
    """
    if not output_path.exists():
        return True
    return input_path.stat().st_mtime > output_path.stat().st_mtime


def convert_file(input_path: Path, force: bool = False) -> Path | None:
    """Convert a markdown file to PDF.

    Args:
        input_path: Path to the markdown file
        force: If True, regenerate even if PDF is up to date

    Returns:
        Path to the generated PDF file, or None if skipped (already up to date)
    """
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    if not input_path.suffix.lower() == ".md":
        raise ValueError(f"Not a markdown file: {input_path}")

    output_path = input_path.with_suffix(".pdf")

    # Skip if PDF is already up to date
    if not force and not needs_rebuild(input_path, output_path):
        return None

    md_content = input_path.read_text(encoding="utf-8")
    title = input_path.stem.replace("-", " ").replace("_", " ").title()

    # Get filename and generation timestamp for traceability
    source_path = input_path.name
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html_content = markdown_to_html(
        md_content,
        title=title,
        source_path=source_path,
        generated_at=generated_at,
    )

    html_to_pdf(
        html_content,
        output_path,
        source_path=source_path,
        generated_at=generated_at,
    )

    return output_path
