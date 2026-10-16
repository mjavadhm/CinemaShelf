"""FastAPI HTTP endpoints for the library module."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.modules.library.models import LibraryItemStatus
from app.modules.library.schemas import (
    CategorizeRequest,
    CategorizeResponse,
    DirectoryBrowseResponse,
    LibraryCreate,
    LibraryItemCreate,
    LibraryItemDetailResponse,
    LibraryItemStatusUpdate,
    LibraryItemSummaryResponse,
    LibraryResponse,
    LibraryRootCreate,
    LibraryRootResponse,
    LibraryStatsResponse,
    MediaFileCreate,
    MediaFileResponse,
    RematchLibraryItemRequest,
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
    response: Response,
    status: Annotated[
        LibraryItemStatus | None, Query(description="Filter by item status")
    ] = None,
    library_id: Annotated[
        int | None, Query(description="Filter by parent library ID")
    ] = None,
    search: Annotated[
        str | None, Query(description="Search title, original title, or imdb ID")
    ] = None,
    genre: Annotated[
        str | None, Query(description="Filter by genre name or persian_name")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    page: Annotated[int | None, Query(ge=1, description="1-indexed page number")] = None,
) -> list[LibraryItemSummaryResponse]:
    """List library items with optional search, genre, status, and library filtering."""
    actual_offset = (page - 1) * limit if page is not None else offset

    total_count = service.count_items(
        status=status,
        library_id=library_id,
        search=search,
        genre=genre,
    )
    items = service.list_items(
        status=status,
        library_id=library_id,
        search=search,
        genre=genre,
        limit=limit,
        offset=actual_offset,
    )

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
    current_page = (actual_offset // limit) + 1 if limit > 0 else 1

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Total-Pages"] = str(total_pages)
    response.headers["X-Current-Page"] = str(current_page)
    response.headers["X-Page-Size"] = str(limit)

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


@router.post(
    "/items/{id}/rematch",
    response_model=LibraryItemDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Rematch a library item and its media files to a different movie or show",
)
async def rematch_library_item(
    id: int,
    request: RematchLibraryItemRequest,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> LibraryItemDetailResponse:
    """Re-identify a library item to a new TMDB ID, transferring associated physical media files."""
    updated = await service.rematch_item(
        item_id=id,
        target_tmdb_id=request.tmdb_id,
        work_type=request.work_type,
    )
    return LibraryItemDetailResponse.model_validate(updated)


@router.post(
    "/by-work/{work_id}/rematch",
    response_model=LibraryItemDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Rematch by work ID to a different movie or show",
)
async def rematch_by_work_id(
    work_id: int,
    request: RematchLibraryItemRequest,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> LibraryItemDetailResponse:
    """Find library item by current work ID and rematch to target TMDB work."""
    item = service.get_item_by_work_id(work_id)
    updated = await service.rematch_item(
        item_id=item.id,
        target_tmdb_id=request.tmdb_id,
        work_type=request.work_type,
    )
    return LibraryItemDetailResponse.model_validate(updated)


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


@router.get(
    "/stats",
    response_model=LibraryStatsResponse,
    summary="Get library statistics and analytics",
)
def get_library_statistics(
    service: Annotated[LibraryService, Depends(get_library_service)],
    library_id: Annotated[int | None, Query(description="Filter stats by library ID")] = None,
) -> LibraryStatsResponse:
    """Retrieve comprehensive analytics across cataloged library items."""
    stats = service.get_library_stats(library_id=library_id)
    return LibraryStatsResponse.model_validate(stats)


@router.post(
    "/categorize",
    response_model=CategorizeResponse,
    summary="Categorize library into virtual shortcut tree",
)
def categorize_library_shortcuts(
    request: CategorizeRequest,
    service: Annotated[LibraryService, Depends(get_library_service)],
) -> CategorizeResponse:
    """Generate categorized virtual shortcuts by director, rating, and decade."""
    result = service.categorize_library(
        destination_path=request.destination_path,
        library_id=request.library_id,
        by_director=request.by_director,
        by_rating=request.by_rating,
        by_decade=request.by_decade,
    )
    return CategorizeResponse.model_validate(result)


