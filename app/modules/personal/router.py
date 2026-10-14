"""FastAPI HTTP endpoints for the personal module."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.modules.personal.models import WatchStatus
from app.modules.personal.schemas import (
    CustomShelfCreateRequest,
    CustomShelfDetailResponse,
    CustomShelfResponse,
    CustomShelfUpdateRequest,
    FavoriteToggleRequest,
    PersonalRecordResponse,
    PersonalRecordUpdateRequest,
    PersonalWorkCatalogItem,
    RatingRequest,
    ShelfItemCreateRequest,
    ShelfItemResponse,
    ShelfReorderRequest,
    WatchDiaryCreateRequest,
    WatchDiaryLogResponse,
    WatchlistToggleRequest,
)
from app.modules.personal.service import PersonalService

router = APIRouter(prefix="/personal", tags=["personal"])


def get_personal_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> PersonalService:
    """Dependency provider for PersonalService."""
    return PersonalService(session)


# -----------------------------------------------------------------------------
# Personal Records
# -----------------------------------------------------------------------------


@router.get(
    "/records/{work_id}",
    response_model=PersonalRecordResponse,
    summary="Get personal record for a work",
)
def get_personal_record(
    work_id: int,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> PersonalRecordResponse:
    """Retrieve user watch status, rating, and notes for a media work."""
    return service.get_personal_record(work_id)


@router.patch(
    "/records/{work_id}",
    response_model=PersonalRecordResponse,
    summary="Update personal record for a work",
)
def update_personal_record(
    work_id: int,
    req: PersonalRecordUpdateRequest,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> PersonalRecordResponse:
    """Update fields on a work's personal record."""
    return service.update_personal_record(work_id, req)


@router.post(
    "/records/{work_id}/watchlist",
    response_model=PersonalRecordResponse,
    summary="Toggle or set watchlist status",
)
def toggle_watchlist(
    work_id: int,
    service: Annotated[PersonalService, Depends(get_personal_service)],
    req: WatchlistToggleRequest | None = None,
) -> PersonalRecordResponse:
    """Toggle or explicitly set watchlist state for a work."""
    target_state = req.in_watchlist if req else None
    return service.toggle_watchlist(work_id, target_state)


@router.post(
    "/records/{work_id}/favorite",
    response_model=PersonalRecordResponse,
    summary="Toggle or set favorite status",
)
def toggle_favorite(
    work_id: int,
    service: Annotated[PersonalService, Depends(get_personal_service)],
    req: FavoriteToggleRequest | None = None,
) -> PersonalRecordResponse:
    """Toggle or explicitly set favorite state for a work."""
    target_state = req.is_favorite if req else None
    return service.toggle_favorite(work_id, target_state)


@router.post(
    "/records/{work_id}/rate",
    response_model=PersonalRecordResponse,
    summary="Rate a work",
)
def rate_work(
    work_id: int,
    req: RatingRequest,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> PersonalRecordResponse:
    """Set or clear personal rating for a work."""
    return service.set_rating(work_id, req.rating)


# -----------------------------------------------------------------------------
# Watch Diary
# -----------------------------------------------------------------------------


@router.post(
    "/diary",
    response_model=WatchDiaryLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a viewing event in the watch diary",
)
def log_watch_event(
    req: WatchDiaryCreateRequest,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> WatchDiaryLogResponse:
    """Log a viewing in the diary and sync personal watch stats."""
    return service.log_watch(req)


@router.get(
    "/diary",
    response_model=list[WatchDiaryLogResponse],
    summary="List watch diary events",
)
def list_diary_logs(
    service: Annotated[PersonalService, Depends(get_personal_service)],
    work_id: Annotated[int | None, Query(description="Filter by media work ID")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[WatchDiaryLogResponse]:
    """List chronologically ordered watch diary entries."""
    return service.list_diary(work_id=work_id, limit=limit, offset=offset)


@router.get(
    "/diary/{log_id}",
    response_model=WatchDiaryLogResponse,
    summary="Get an individual diary log entry",
)
def get_diary_log(
    log_id: int,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> WatchDiaryLogResponse:
    """Fetch a single watch diary entry by ID."""
    return service.get_diary_entry(log_id)


@router.delete(
    "/diary/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a diary log entry",
)
def delete_diary_log(
    log_id: int,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> Response:
    """Delete a diary entry and recalculate work watch count."""
    service.delete_diary_entry(log_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -----------------------------------------------------------------------------
# Custom Shelves
# -----------------------------------------------------------------------------


@router.post(
    "/shelves",
    response_model=CustomShelfResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom shelf",
)
def create_shelf(
    req: CustomShelfCreateRequest,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> CustomShelfResponse:
    """Create a new user-curated shelf or collection."""
    return service.create_shelf(
        name=req.name,
        description=req.description,
        is_smart_shelf=req.is_smart_shelf,
    )


@router.get(
    "/shelves",
    response_model=list[CustomShelfResponse],
    summary="List all custom shelves",
)
def list_shelves(
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> list[CustomShelfResponse]:
    """List all custom shelves with item counts."""
    return service.list_shelves()


@router.get(
    "/shelves/{shelf_id_or_slug}",
    response_model=CustomShelfDetailResponse,
    summary="Get custom shelf details and member items",
)
def get_shelf_detail(
    shelf_id_or_slug: str,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> CustomShelfDetailResponse:
    """Fetch details and member works of a custom shelf by ID or slug."""
    return service.get_shelf(shelf_id_or_slug)


@router.patch(
    "/shelves/{shelf_id}",
    response_model=CustomShelfResponse,
    summary="Update a custom shelf",
)
def update_shelf(
    shelf_id: int,
    req: CustomShelfUpdateRequest,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> CustomShelfResponse:
    """Update name or description of a custom shelf."""
    return service.update_shelf(
        shelf_id=shelf_id,
        name=req.name,
        description=req.description,
    )


@router.delete(
    "/shelves/{shelf_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custom shelf",
)
def delete_shelf(
    shelf_id: int,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> Response:
    """Delete a custom shelf and all its item mappings."""
    service.delete_shelf(shelf_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/shelves/{shelf_id}/items",
    response_model=ShelfItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a work to a custom shelf",
)
def add_item_to_shelf(
    shelf_id: int,
    req: ShelfItemCreateRequest,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> ShelfItemResponse:
    """Add a work to a shelf or update its rank order and note."""
    return service.add_to_shelf(
        shelf_id=shelf_id,
        work_id=req.work_id,
        rank_order=req.rank_order,
        note=req.note,
    )


@router.delete(
    "/shelves/{shelf_id}/items/{work_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a work from a custom shelf",
)
def remove_item_from_shelf(
    shelf_id: int,
    work_id: int,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> Response:
    """Remove a member work from a shelf."""
    service.remove_from_shelf(shelf_id, work_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/shelves/{shelf_id}/items/reorder",
    response_model=list[ShelfItemResponse],
    summary="Reorder items in a custom shelf",
)
def reorder_shelf_items(
    shelf_id: int,
    req: ShelfReorderRequest,
    service: Annotated[PersonalService, Depends(get_personal_service)],
) -> list[ShelfItemResponse]:
    """Reorder items in a shelf according to a provided ordered list of work IDs."""
    return service.reorder_shelf(shelf_id, req.work_ids)


# -----------------------------------------------------------------------------
# Catalog Filtering by Personal Attributes
# -----------------------------------------------------------------------------


@router.get(
    "/works",
    response_model=list[PersonalWorkCatalogItem],
    summary="Filter library works with personal criteria",
)
def filter_personal_catalog(
    service: Annotated[PersonalService, Depends(get_personal_service)],
    watch_status: Annotated[WatchStatus | None, Query()] = None,
    in_watchlist: Annotated[bool | None, Query()] = None,
    is_favorite: Annotated[bool | None, Query()] = None,
    min_rating: Annotated[float | None, Query(ge=0.0, le=10.0)] = None,
    max_rating: Annotated[float | None, Query(ge=0.0, le=10.0)] = None,
    shelf_id: Annotated[int | None, Query()] = None,
    genre_id: Annotated[int | None, Query()] = None,
    sort_by: Annotated[str, Query()] = "updated_at",
    sort_order: Annotated[str, Query()] = "desc",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PersonalWorkCatalogItem]:
    """Filter catalog works based on rating, watchlist, favorites, watch status, and shelves."""
    return service.filter_catalog(
        watch_status=watch_status,
        in_watchlist=in_watchlist,
        is_favorite=is_favorite,
        min_rating=min_rating,
        max_rating=max_rating,
        shelf_id=shelf_id,
        genre_id=genre_id,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
