"""File browser service for directory listing and folder tree."""

from datetime import datetime
from pathlib import Path

from ..models import DirectoryListing, FileItem, FileType, FolderNode, SortField, SortOrder

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}


def get_file_type(path: Path) -> FileType:
    """Determine the type of a file or directory."""
    if path.is_dir():
        return FileType.DIRECTORY
    ext = path.suffix.lower()
    if ext == ".md":
        return FileType.MARKDOWN
    if ext in IMAGE_EXTENSIONS:
        return FileType.IMAGE
    return FileType.OTHER


def list_directory(
    root_path: Path,
    relative_path: str = "",
    sort_field: SortField = SortField.NAME,
    sort_order: SortOrder = SortOrder.ASC,
    show_hidden: bool = False,
) -> DirectoryListing:
    """List contents of a directory with sorting."""
    target = root_path / relative_path if relative_path else root_path

    if not target.exists() or not target.is_dir():
        return DirectoryListing(
            path=relative_path or "",
            parent=str(Path(relative_path).parent) if relative_path else None,
            items=[],
            breadcrumbs=_build_breadcrumbs(relative_path),
        )

    items = []
    for entry in target.iterdir():
        if not show_hidden and entry.name.startswith("."):
            continue

        file_type = get_file_type(entry)

        # Only include markdown, images, and directories
        if file_type == FileType.OTHER:
            continue

        try:
            stat = entry.stat()
            items.append(
                FileItem(
                    name=entry.name,
                    path=str(entry.relative_to(root_path)),
                    type=file_type,
                    size=stat.st_size if entry.is_file() else None,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    extension=entry.suffix.lower() if entry.is_file() else None,
                )
            )
        except (OSError, ValueError):
            # Skip files we can't access
            continue

    # Sort items (directories first, then by specified field)
    def sort_key(item: FileItem):
        is_dir = 0 if item.type == FileType.DIRECTORY else 1
        if sort_field == SortField.NAME:
            return (is_dir, item.name.lower())
        elif sort_field == SortField.DATE:
            return (is_dir, item.modified)
        elif sort_field == SortField.SIZE:
            return (is_dir, item.size or 0)
        return (is_dir, item.name.lower())

    items.sort(key=sort_key, reverse=(sort_order == SortOrder.DESC))

    return DirectoryListing(
        path=relative_path or "",
        parent=str(Path(relative_path).parent) if relative_path else None,
        items=items,
        breadcrumbs=_build_breadcrumbs(relative_path),
    )


def _build_breadcrumbs(relative_path: str) -> list[dict[str, str]]:
    """Build breadcrumb navigation from a path."""
    breadcrumbs = [{"name": "Home", "path": ""}]
    if relative_path:
        parts = Path(relative_path).parts
        for i, part in enumerate(parts):
            breadcrumbs.append(
                {
                    "name": part,
                    "path": str(Path(*parts[: i + 1])),
                }
            )
    return breadcrumbs


def build_folder_tree(
    root_path: Path,
    relative_path: str = "",
    max_depth: int = 10,
    current_depth: int = 0,
) -> list[FolderNode]:
    """Build a folder tree structure for the sidebar, including markdown files."""
    if current_depth >= max_depth:
        return []

    target = root_path / relative_path if relative_path else root_path

    if not target.exists() or not target.is_dir():
        return []

    folders = []
    files = []
    try:
        entries = sorted(target.iterdir(), key=lambda x: x.name.lower())
    except OSError:
        return []

    for entry in entries:
        if entry.name.startswith("."):
            continue

        rel_path = str(entry.relative_to(root_path))

        if entry.is_dir():
            children = build_folder_tree(root_path, rel_path, max_depth, current_depth + 1)
            has_markdown = _has_markdown_files(entry)

            folders.append(
                FolderNode(
                    name=entry.name,
                    path=rel_path,
                    children=children,
                    has_markdown=has_markdown,
                    is_file=False,
                )
            )
        elif entry.suffix.lower() == ".md":
            # Include markdown files in the tree
            files.append(
                FolderNode(
                    name=entry.stem,  # Use stem (filename without extension)
                    path=rel_path,
                    children=[],
                    has_markdown=True,
                    is_file=True,
                )
            )

    # Return folders first, then files
    return folders + files


def _has_markdown_files(directory: Path) -> bool:
    """Check if a directory contains any markdown files."""
    try:
        for entry in directory.iterdir():
            if entry.suffix.lower() == ".md":
                return True
    except OSError:
        pass
    return False


def get_all_markdown_files(
    root_path: Path,
    sort_field: SortField = SortField.NAME,
    sort_order: SortOrder = SortOrder.ASC,
) -> list[dict]:
    """Get all markdown files recursively as a flat list.

    Returns a list of dicts with:
        - name: filename without extension
        - path: relative path to file
        - directory: parent directory path (empty string for root)
        - modified: modification datetime
    """
    files = []

    def scan_directory(directory: Path):
        try:
            for entry in directory.iterdir():
                if entry.name.startswith("."):
                    continue
                if entry.is_dir():
                    scan_directory(entry)
                elif entry.suffix.lower() == ".md":
                    rel_path = str(entry.relative_to(root_path))
                    parent_dir = str(entry.parent.relative_to(root_path))
                    if parent_dir == ".":
                        parent_dir = ""
                    try:
                        stat = entry.stat()
                        files.append({
                            "name": entry.stem,
                            "path": rel_path,
                            "directory": parent_dir,
                            "modified": datetime.fromtimestamp(stat.st_mtime),
                        })
                    except OSError:
                        pass
        except OSError:
            pass

    scan_directory(root_path)

    # Sort files
    if sort_field == SortField.NAME:
        files.sort(key=lambda f: f["name"].lower(), reverse=(sort_order == SortOrder.DESC))
    elif sort_field == SortField.DATE:
        files.sort(key=lambda f: f["modified"], reverse=(sort_order == SortOrder.DESC))

    return files
