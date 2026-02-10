"""Markdown rendering service for web preview."""

import re
from datetime import datetime
from pathlib import Path

from ...converter import markdown_to_html, get_pygments_css


def extract_title(md_content: str) -> str | None:
    """Extract title from first H1 header in markdown content."""
    match = re.search(r"^#\s+(.+)$", md_content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def render_markdown_for_web(file_path: Path, root_path: Path) -> dict:
    """Render markdown file for web preview.

    Returns dict with html content, title, and metadata.
    """
    content = file_path.read_text(encoding="utf-8")
    relative_path = str(file_path.relative_to(root_path))

    # Extract title from first H1, fallback to filename
    title = extract_title(content) or file_path.stem.replace("-", " ").replace("_", " ").title()

    # Reuse existing conversion with client-side mermaid for fast loading
    html = markdown_to_html(
        content,
        title=title,
        source_path=relative_path,
        generated_at=None,  # Not needed for web
        client_side_mermaid=True,  # Let browser render mermaid diagrams
    )

    # Get modification time
    modified = datetime.fromtimestamp(file_path.stat().st_mtime)

    return {
        "html": html,
        "title": title,
        "path": relative_path,
        "modified": modified,
        "pygments_css": get_pygments_css(),
    }
