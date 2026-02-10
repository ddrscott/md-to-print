"""Pydantic models for the server API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class SortField(str, Enum):
    """Field to sort files by."""

    NAME = "name"
    DATE = "date"
    SIZE = "size"


class SortOrder(str, Enum):
    """Sort order direction."""

    ASC = "asc"
    DESC = "desc"


class FileType(str, Enum):
    """Type of file in the directory listing."""

    MARKDOWN = "markdown"
    IMAGE = "image"
    DIRECTORY = "directory"
    OTHER = "other"


class FileItem(BaseModel):
    """A file or directory item in a listing."""

    name: str
    path: str  # Relative to root
    type: FileType
    size: int | None = None
    modified: datetime
    extension: str | None = None


class DirectoryListing(BaseModel):
    """Response for directory listing."""

    path: str
    parent: str | None
    items: list[FileItem]
    breadcrumbs: list[dict[str, str]]


class FolderNode(BaseModel):
    """A node in the folder tree (can represent folders or files)."""

    name: str
    path: str
    children: list["FolderNode"] = []
    has_markdown: bool = False
    expanded: bool = False
    is_file: bool = False  # True for markdown files, False for directories


class PreviewResponse(BaseModel):
    """Response for markdown preview."""

    path: str
    title: str
    html: str
    modified: datetime


class FileChangeEvent(BaseModel):
    """Event sent via SSE when a file changes."""

    event_type: str  # "created", "modified", "deleted"
    path: str
    file_type: FileType
    timestamp: datetime
    affected_folder: str
