"""HTML page routes for the markdown viewer."""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..services import build_folder_tree, get_all_markdown_files, get_file_type, list_directory, render_markdown_for_web
from ..models import FileType, SortField, SortOrder
from .api import get_root_path, validate_path

router = APIRouter()

# Templates directory
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    path: str = "",
    sort: SortField = SortField.NAME,
    order: SortOrder = SortOrder.ASC,
    minimal: bool = False,
    root_path: Path = Depends(get_root_path),
):
    """Main viewer page - file browser or markdown preview."""
    target_path = validate_path(root_path, path)

    # Get flat file list for sidebar (skip in minimal mode for faster single-file viewing)
    all_files = [] if minimal else get_all_markdown_files(root_path, sort, order)

    # Determine if viewing a file or directory
    if target_path.is_file() and target_path.suffix.lower() == ".md":
        # Viewing a markdown file
        preview_data = render_markdown_for_web(target_path, root_path)
        listing = None if minimal else list_directory(root_path, str(target_path.parent.relative_to(root_path)) if target_path.parent != root_path else "", sort, order)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "all_files": all_files,
                "listing": listing,
                "preview": preview_data,
                "current_path": path,
                "current_file": path,
                "sort": sort.value,
                "order": order.value,
                "is_file_view": True,
                "minimal": minimal,
            },
        )
    else:
        # Viewing a directory (show placeholder)
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "all_files": all_files,
                "listing": None,
                "preview": None,
                "current_path": path,
                "current_file": None,
                "sort": sort.value,
                "order": order.value,
                "is_file_view": False,
                "minimal": minimal,
            },
        )


@router.get("/view/{path:path}", response_class=HTMLResponse)
async def view_file(
    request: Request,
    path: str,
    minimal: bool = False,
    root_path: Path = Depends(get_root_path),
):
    """View a specific file or folder."""
    # Redirect to main page with path parameter
    from fastapi.responses import RedirectResponse
    minimal_param = "&minimal=true" if minimal else ""
    return RedirectResponse(url=f"/?path={path}{minimal_param}", status_code=302)


# HTMX partial endpoints
@router.get("/partials/sidebar", response_class=HTMLResponse)
async def partial_sidebar(
    request: Request,
    current_path: str = "",
    root_path: Path = Depends(get_root_path),
):
    """Render just the sidebar folder tree."""
    folder_tree = build_folder_tree(root_path)
    return templates.TemplateResponse(
        "partials/sidebar.html",
        {
            "request": request,
            "folder_tree": folder_tree,
            "current_path": current_path,
        },
    )


@router.get("/partials/file-list", response_class=HTMLResponse)
async def partial_file_list(
    request: Request,
    path: str = "",
    sort: SortField = SortField.NAME,
    order: SortOrder = SortOrder.ASC,
    root_path: Path = Depends(get_root_path),
):
    """Render just the file listing."""
    listing = list_directory(root_path, path, sort, order)
    return templates.TemplateResponse(
        "partials/file_list.html",
        {
            "request": request,
            "listing": listing,
            "sort": sort.value,
            "order": order.value,
        },
    )


@router.get("/partials/preview", response_class=HTMLResponse)
async def partial_preview(
    request: Request,
    path: str,
    root_path: Path = Depends(get_root_path),
):
    """Render just the markdown preview."""
    target_path = validate_path(root_path, path)

    if not target_path.is_file() or target_path.suffix.lower() != ".md":
        return HTMLResponse("<div class='p-4 text-error'>Not a markdown file</div>")

    preview_data = render_markdown_for_web(target_path, root_path)
    return templates.TemplateResponse(
        "partials/preview.html",
        {
            "request": request,
            "preview": preview_data,
        },
    )
