"""REST API endpoints for the markdown viewer."""

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from ..models import DirectoryListing, FolderNode, PreviewResponse, SortField, SortOrder
from ..services import build_folder_tree, get_file_type, list_directory, render_markdown_for_web
from ..services.file_browser import IMAGE_EXTENSIONS

router = APIRouter(prefix="/api/v1")


def get_root_path(request: Request) -> Path:
    """Get root path from app state."""
    return request.app.state.root_path


def validate_path(root_path: Path, requested_path: str) -> Path:
    """Validate that requested path is within root directory.

    Prevents directory traversal attacks.
    """
    if not requested_path:
        return root_path

    # Normalize and resolve
    target = (root_path / requested_path).resolve()

    # Ensure it's within root
    try:
        target.relative_to(root_path.resolve())
    except ValueError:
        raise HTTPException(
            status_code=403, detail="Access denied: path outside root directory"
        )

    return target


@router.get("/files", response_model=DirectoryListing)
async def list_files(
    path: str = "",
    sort: SortField = SortField.NAME,
    order: SortOrder = SortOrder.ASC,
    root_path: Path = Depends(get_root_path),
):
    """List files and folders in a directory."""
    validate_path(root_path, path)
    return list_directory(root_path, path, sort, order)


@router.get("/tree", response_model=list[FolderNode])
async def get_folder_tree(
    path: str = "",
    depth: int = 10,
    root_path: Path = Depends(get_root_path),
):
    """Get folder tree structure for sidebar navigation."""
    validate_path(root_path, path)
    return build_folder_tree(root_path, path, max_depth=depth)


@router.get("/preview", response_model=PreviewResponse)
async def preview_markdown(
    path: str,
    root_path: Path = Depends(get_root_path),
):
    """Render markdown file as HTML for preview."""
    file_path = validate_path(root_path, path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if file_path.suffix.lower() != ".md":
        raise HTTPException(status_code=400, detail="Not a markdown file")

    try:
        result = render_markdown_for_web(file_path, root_path)
        return PreviewResponse(
            path=result["path"],
            title=result["title"],
            html=result["html"],
            modified=result["modified"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering markdown: {e}")


@router.get("/raw")
async def get_raw_content(
    path: str,
    root_path: Path = Depends(get_root_path),
):
    """Get raw file content."""
    file_path = validate_path(root_path, path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    try:
        content = file_path.read_text(encoding="utf-8")
        return {"path": path, "content": content}
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not text")


@router.get("/image/{path:path}")
async def serve_image(
    path: str,
    root_path: Path = Depends(get_root_path),
):
    """Serve image files from the root directory."""
    file_path = validate_path(root_path, path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Not an image file")

    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(file_path, media_type=media_type or "application/octet-stream")
