"""FastAPI HTTP endpoints for the playback module."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.modules.playback.schemas import (
    FileAccessResponse,
    WatchedWorkItemResponse,
    WatchStatusResponse,
)
from app.modules.playback.service import PlaybackService

router = APIRouter(prefix="/playback", tags=["playback"])


def get_playback_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> PlaybackService:
    """Dependency injector for PlaybackService."""
    return PlaybackService(session=session)


# --- File Access & Launching ---


@router.post("/files/{id}/open", response_model=FileAccessResponse)
def open_media_file(
    id: int,
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> FileAccessResponse:
    """Open physical media file with the operating system default application."""
    return service.open_media_file(media_file_id=id)


@router.post("/works/{id}/open", response_model=FileAccessResponse)
def open_work(
    id: int,
    service: Annotated[PlaybackService, Depends(get_playback_service)],
    episode_id: Annotated[int | None, Query(description="Specific episode ID")] = None,
) -> FileAccessResponse:
    """Open local media file associated with a movie or episode."""
    return service.open_work(work_id=id, episode_id=episode_id)


@router.post("/files/{id}/open-location", response_model=FileAccessResponse)
def open_file_location(
    id: int,
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> FileAccessResponse:
    """Reveal the folder containing the media file in the OS file manager."""
    return service.open_file_location(media_file_id=id)


# --- Manual Watch Status Toggles ---


@router.post("/works/{id}/mark-watched", response_model=WatchStatusResponse)
def mark_work_watched(
    id: int,
    service: Annotated[PlaybackService, Depends(get_playback_service)],
    episode_id: Annotated[int | None, Query(description="Specific episode ID")] = None,
) -> WatchStatusResponse:
    """Manually mark a film or episode as watched."""
    progress = service.mark_watched(work_id=id, episode_id=episode_id)
    return WatchStatusResponse(
        work_id=progress.work_id,
        episode_id=progress.episode_id,
        is_watched=progress.is_completed,
        last_watched_at=progress.last_watched_at,
    )


@router.post("/works/{id}/mark-unwatched", response_model=WatchStatusResponse)
def mark_work_unwatched(
    id: int,
    service: Annotated[PlaybackService, Depends(get_playback_service)],
    episode_id: Annotated[int | None, Query(description="Specific episode ID")] = None,
) -> WatchStatusResponse:
    """Manually reset a film or episode to unwatched."""
    progress = service.mark_unwatched(work_id=id, episode_id=episode_id)
    return WatchStatusResponse(
        work_id=progress.work_id,
        episode_id=progress.episode_id,
        is_watched=progress.is_completed,
        last_watched_at=progress.last_watched_at,
    )


@router.get("/works/{id}/status", response_model=WatchStatusResponse)
def get_watch_status(
    id: int,
    service: Annotated[PlaybackService, Depends(get_playback_service)],
    episode_id: Annotated[int | None, Query(description="Specific episode ID")] = None,
) -> WatchStatusResponse:
    """Get the current watched status and timestamp for a film or episode."""
    return service.get_watch_status(work_id=id, episode_id=episode_id)


# --- History & Watched Listings ---


@router.get("/watched", response_model=list[WatchedWorkItemResponse])
def list_watched_works(
    service: Annotated[PlaybackService, Depends(get_playback_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[WatchedWorkItemResponse]:
    """List works manually marked as watched."""
    items = service.list_watched(limit=limit, offset=offset)
    return [WatchedWorkItemResponse.model_validate(p) for p in items]


@router.get("/recently-opened", response_model=list[WatchedWorkItemResponse])
def list_recently_opened_works(
    service: Annotated[PlaybackService, Depends(get_playback_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[WatchedWorkItemResponse]:
    """List works recently accessed or opened in the OS."""
    items = service.list_recently_opened(limit=limit, offset=offset)
    return [WatchedWorkItemResponse.model_validate(p) for p in items]
