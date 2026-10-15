"""FastAPI HTTP endpoints for the library module."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.modules.library.models import LibraryItemStatus
from app.modules.library.schemas import (
    DirectoryBrowseResponse,
    LibraryCreate,
    LibraryItemCreate,
    LibraryItemDetailResponse,
    LibraryItemStatusUpdate,
    LibraryItemSummaryResponse,
    LibraryResponse,
    LibraryRootCreate,
    LibraryRootResponse,
    MediaFileCreate,
    MediaFileResponse,
    ScanJobResponse,
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
    library_id: Annotated[
        int | None, Query(description="Filter by parent library ID")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[LibraryItemSummaryResponse]:
    """List library items with optional status and library filtering."""
    items = service.list_items(
        status=status, library_id=library_id, limit=limit, offset=offset
    )
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


# -----------------------------------------------------------------------------
# Multi-Library & Storage Roots Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/libraries",
    response_model=LibraryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new named library",
)
def create_library(
    request: LibraryCreate,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> LibraryResponse:
    """Create a new media library collection (e.g. Movies, 4K UHD, Series)."""
    return service.create_library(request)


@router.get(
    "/libraries",
    response_model=list[LibraryResponse],
    summary="List all configured libraries",
)
def list_libraries(
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> list[LibraryResponse]:
    """List all user libraries with their storage roots and item counts."""
    return service.list_libraries()


@router.get(
    "/libraries/{id}",
    response_model=LibraryResponse,
    summary="Get library details",
)
def get_library(
    id: int,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> LibraryResponse:
    """Retrieve a specific library and its roots."""
    return service.get_library(id)


@router.delete(
    "/libraries/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a library",
)
def delete_library(
    id: int,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> Response:
    """Delete a library collection."""
    service.delete_library(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/libraries/{id}/roots",
    response_model=LibraryRootResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add storage root folder to library",
)
def add_library_root(
    id: int,
    request: LibraryRootCreate,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> LibraryRootResponse:
    """Register a physical filesystem folder path as a root under this library."""
    return service.add_root_to_library(id, request)


@router.delete(
    "/roots/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a storage root",
)
def remove_library_root(
    id: int,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> Response:
    """Remove a storage root from its library."""
    service.remove_root(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/libraries/{id}/scan",
    response_model=ScanJobResponse,
    summary="Trigger filesystem scan on library roots",
)
async def trigger_library_scan(
    id: int,
    service: Annotated[LibraryService, Depends(get_library_service)],
    root_id: Annotated[int | None, Query(description="Specific root to scan")] = None,
) -> ScanJobResponse:
    """Scan root directories, discover video files, parse metadata, and register films."""
    return await service.trigger_scan(id, root_id)


@router.get(
    "/libraries/{id}/scan-jobs",
    response_model=list[ScanJobResponse],
    summary="List scan jobs for a library",
)
def list_library_scan_jobs(
    id: int,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> list[ScanJobResponse]:
    """Retrieve history of scan jobs executed for this library."""
    return service.list_scan_jobs(id)


@router.get(
    "/directories/browse",
    response_model=DirectoryBrowseResponse,
    summary="Browse server filesystem directories",
)
def browse_server_directories(
    service: Annotated[LibraryService, Depends(get_library_service)],
    path: Annotated[str | None, Query(description="Target directory to inspect")] = None,
) -> DirectoryBrowseResponse:
    """Safely browse server directories for folder picker dialogs."""
    return service.browse_directories(path)


