"""Markdown to PDF converter using WeasyPrint."""

import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from html import escape
from pathlib import Path

import markdown
import yaml
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


def _wrap_h1_with_content(html: str) -> str:
    """Wrap H1 headers with their following content to prevent orphans.

    In markdown, `---` creates section breaks. H1s after these should
    start on a new page with at least the first paragraph of content.

    WeasyPrint doesn't reliably handle break-before on column-spanning
    elements inside a multi-column container. We close and reopen the
    article tag to force a true page break, then wrap the H1 and its
    first content element to keep them together.

    The first H1 (Part 1) stays in the normal flow on page 1.
    Subsequent H1s after <hr> start on new pages.
    """
    # Pattern: <hr> followed by <h1>...</h1> and first block element
    # Use [^<]* for H1 content to prevent crossing tag boundaries
    # Include h2 as valid first element (common in documents)
    pattern = re.compile(
        r'<hr\s*/?>(\s*)<h1([^>]*)>([^<]*(?:<(?!/h1)[^<]*)*)</h1>(\s*)(<(?:p|ul|ol|div|blockquote|table|pre|h2)[^>]*>.*?</(?:p|ul|ol|div|blockquote|table|pre|h2)>)',
        re.DOTALL | re.IGNORECASE
    )

    matches = list(pattern.finditer(html))

    if not matches:
        return html

    # Work backwards to preserve positions
    for match in reversed(matches):
        start, end = match.start(), match.end()
        whitespace1 = match.group(1)
        h1_attrs = match.group(2)
        h1_content = match.group(3)
        whitespace2 = match.group(4)
        first_element = match.group(5)

        # Close article, start new article with page break, wrap H1 + content
        replacement = (
            f'</article>'
            f'<article class="new-page">'
            f'<div class="h1-section">{whitespace1}'
            f'<h1{h1_attrs}>{h1_content}</h1>{whitespace2}'
            f'{first_element}'
            f'</div>'
        )
        html = html[:start] + replacement + html[end:]

    return html


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


def _process_mermaid_blocks(md_content: str, client_side: bool = False) -> str:
    """Extract and render mermaid code blocks before markdown processing.

    Args:
        md_content: Raw markdown text
        client_side: If True, preserve mermaid blocks for browser rendering
                     instead of server-side rendering with mmdc
    """
    mermaid_pattern = re.compile(
        r'```mermaid\s*\n(.*?)\n```',
        re.DOTALL | re.IGNORECASE
    )

    def replace_mermaid(match: re.Match) -> str:
        code = match.group(1).strip()
        if client_side:
            # Keep code for client-side rendering with mermaid.js
            return f'\n\n<div class="mermaid-wrapper"><pre class="mermaid">{code}</pre></div>\n\n'
        else:
            # Server-side rendering with mmdc CLI
            svg = _render_mermaid(code)
            return f'\n\n<div class="mermaid-wrapper">{svg}</div>\n\n'

    return mermaid_pattern.sub(replace_mermaid, md_content)


def _process_ascii_diagram_blocks(md_content: str) -> str:
    """Process ASCII diagram code blocks for client-side rendering with svgbob/bob-wasm.

    Recognizes code blocks with language: ascii, bob, svgbob
    """
    ascii_pattern = re.compile(
        r'```(ascii|bob|svgbob)\s*\n(.*?)\n```',
        re.DOTALL | re.IGNORECASE
    )

    def replace_ascii(match: re.Match) -> str:
        lang = match.group(1).lower()
        code = match.group(2)
        # Preserve the code for client-side rendering with bob-wasm
        # Use a pre with data-lang attribute for detection
        escaped_code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'\n\n<div class="ascii-wrapper"><pre class="ascii" data-lang="{lang}">{escaped_code}</pre></div>\n\n'

    return ascii_pattern.sub(replace_ascii, md_content)


def extract_front_matter(md_content: str) -> tuple[dict | None, str]:
    """Extract YAML front matter from markdown content.

    Returns tuple of (front_matter_dict, content_without_front_matter).
    If no front matter found, returns (None, original_content).
    """
    pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(pattern, md_content, re.DOTALL)

    if not match:
        return None, md_content

    try:
        front_matter = yaml.safe_load(match.group(1))
        content_without_fm = md_content[match.end():]
        return front_matter, content_without_fm
    except yaml.YAMLError:
        return None, md_content


def front_matter_to_html(front_matter: dict, include_target_blank: bool = False) -> str:
    """Convert front matter dict to a styled definition list HTML.

    Args:
        front_matter: Dict of front matter key/value pairs
        include_target_blank: If True, add target="_blank" to links (for web)
    """
    if not front_matter:
        return ""

    items = []
    for key, value in front_matter.items():
        display_key = key.replace("_", " ").title()

        if isinstance(value, str):
            if value.startswith(("http://", "https://")):
                target_attr = ' target="_blank" rel="noopener"' if include_target_blank else ''
                display_value = f'<a href="{escape(value)}"{target_attr}>{escape(value)}</a>'
            else:
                display_value = escape(value)
        elif isinstance(value, list):
            display_value = ", ".join(escape(str(v)) for v in value)
        elif value is None:
            display_value = '<span class="fm-null">—</span>'
        else:
            display_value = escape(str(value))

        items.append(f'<dt>{escape(display_key)}</dt><dd>{display_value}</dd>')

    return f'<dl class="front-matter">\n{"".join(items)}\n</dl>'


def markdown_to_html(
    md_content: str,
    title: str = "Document",
    source_path: str | None = None,
    generated_at: str | None = None,
    client_side_mermaid: bool = False,
) -> str:
    """Convert markdown content to a full HTML document.

    Args:
        md_content: Raw markdown text
        title: Document title for the HTML head
        source_path: Absolute path to source file (for footer)
        generated_at: Generation timestamp (for footer)
        client_side_mermaid: If True, preserve mermaid blocks for browser rendering

    Returns:
        Complete HTML document as string
    """
    # Extract front matter before any processing
    front_matter, md_content = extract_front_matter(md_content)
    front_matter_html = front_matter_to_html(front_matter) if front_matter else ""

    # Process mermaid blocks first (before markdown conversion)
    md_content = _process_mermaid_blocks(md_content, client_side=client_side_mermaid)
    # Process ASCII diagram blocks for client-side rendering
    md_content = _process_ascii_diagram_blocks(md_content)

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
    html_body = _wrap_h1_with_content(html_body)
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
{front_matter_html}
{html_body}
    </article>
</body>
</html>"""

    return html_doc


def markdown_to_html_body(
    md_content: str,
    client_side_mermaid: bool = True,
) -> tuple[str, str]:
    """Convert markdown content to HTML body content only (no document wrapper).

    Args:
        md_content: Raw markdown text
        client_side_mermaid: If True, preserve mermaid blocks for browser rendering

    Returns:
        Tuple of (html_body, pygments_css)
    """
    # Process mermaid blocks first (before markdown conversion)
    md_content = _process_mermaid_blocks(md_content, client_side=client_side_mermaid)
    # Process ASCII diagram blocks for client-side rendering
    md_content = _process_ascii_diagram_blocks(md_content)

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
    html_body = _wrap_h1_with_content(html_body)
    pygments_css = get_pygments_css()

    return html_body, pygments_css


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


def convert_file(input_path: Path, force: bool = False, debug: bool = False) -> Path | None:
    """Convert a markdown file to PDF.

    Args:
        input_path: Path to the markdown file
        force: If True, regenerate even if PDF is up to date
        debug: If True, save intermediate HTML file alongside PDF

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

    # Save intermediate HTML for debugging
    if debug:
        html_path = input_path.with_suffix(".html")
        html_path.write_text(html_content, encoding="utf-8")

    html_to_pdf(
        html_content,
        output_path,
        source_path=source_path,
        generated_at=generated_at,
    )

    return output_path
