"""FastAPI HTTP endpoints for the library module."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.modules.library.models import LibraryItemStatus
from app.modules.library.schemas import (
    LibraryItemCreate,
    LibraryItemDetailResponse,
    LibraryItemStatusUpdate,
    LibraryItemSummaryResponse,
    MediaFileCreate,
    MediaFileResponse,
    StorageVolumeResponse,
)
from app.modules.library.service import LibraryService

router = APIRouter(prefix="/library", tags=["library"])


def get_library_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> LibraryService:
    """Dependency injector for LibraryService."""
    return LibraryService(session=session)


@router.post(
    "/items",
    response_model=LibraryItemDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_item_to_library(
    request: LibraryItemCreate,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> LibraryItemDetailResponse:
    """Add a work to the user's local library."""
    item = await service.add_to_library(request)
    return LibraryItemDetailResponse.model_validate(item)


@router.get("/items", response_model=list[LibraryItemSummaryResponse])
def list_library_items(
    service: Annotated[LibraryService, Depends(get_library_service)],
    status: Annotated[
        LibraryItemStatus | None, Query(description="Filter by item status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[LibraryItemSummaryResponse]:
    """List library items with optional status filtering."""
    items = service.list_items(status=status, limit=limit, offset=offset)
    return [LibraryItemSummaryResponse.model_validate(item) for item in items]


@router.get("/items/{id}", response_model=LibraryItemDetailResponse)
def get_library_item(
    id: int,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> LibraryItemDetailResponse:
    """Retrieve detailed library item information including physical media files."""
    item = service.get_item(id)
    return LibraryItemDetailResponse.model_validate(item)


@router.patch("/items/{id}/status", response_model=LibraryItemDetailResponse)
def update_library_item_status(
    id: int,
    request: LibraryItemStatusUpdate,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> LibraryItemDetailResponse:
    """Update acquisition/availability status of a library item."""
    item = service.update_status(id, request.status)
    return LibraryItemDetailResponse.model_validate(item)


@router.post(
    "/items/{id}/files",
    response_model=MediaFileResponse,
    status_code=status.HTTP_201_CREATED,
)
def attach_media_file(
    id: int,
    request: MediaFileCreate,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> MediaFileResponse:
    """Register a local video file under this library item."""
    media_file = service.attach_media_file(id, request)
    return MediaFileResponse.model_validate(media_file)


@router.delete("/items/{id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_library_item(
    id: int,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> Response:
    """Remove a library item entry from catalog."""
    service.remove_item(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/by-work/{work_id}", response_model=LibraryItemDetailResponse)
def get_library_item_by_work(
    work_id: int,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> LibraryItemDetailResponse:
    """Retrieve library item and files corresponding to a MediaWork ID."""
    item = service.get_item_by_work_id(work_id)
    return LibraryItemDetailResponse.model_validate(item)


@router.get("/volumes", response_model=list[StorageVolumeResponse])
def list_storage_volumes(
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> list[StorageVolumeResponse]:
    """Retrieve status, online availability, and disk usage for storage drives."""
    return service.get_storage_volumes()

