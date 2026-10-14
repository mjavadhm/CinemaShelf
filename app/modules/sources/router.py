"""FastAPI HTTP endpoints for the sources module."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.modules.sources.models import DownloadTaskStatus
from app.modules.sources.schemas import (
    Aria2StatsResponse,
    DiscoverReleasesResponse,
    DownloadTaskCreate,
    DownloadTaskResponse,
    SourceReleaseResponse,
    SpeedLimitRequest,
)
from app.modules.sources.service import SourcesService

router = APIRouter(prefix="/sources", tags=["sources"])


def get_sources_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> SourcesService:
    """Dependency injector for SourcesService."""
    return SourcesService(session=session)


# --- Releases & Scraping ---


@router.post("/works/{id}/discover", response_model=DiscoverReleasesResponse)
def discover_releases_for_work(
    id: int,
    service: Annotated[SourcesService, Depends(get_sources_service)],
) -> DiscoverReleasesResponse:
    """Scrape Zarfilm for available releases of a work and persist them."""
    page_url, releases = service.discover_and_save_releases(work_id=id)
    return DiscoverReleasesResponse(
        work_id=id,
        source_page_url=page_url,
        total_found=len(releases),
        releases=[SourceReleaseResponse.model_validate(r) for r in releases],
    )


@router.get("/works/{id}/releases", response_model=list[SourceReleaseResponse])
def list_releases_for_work(
    id: int,
    service: Annotated[SourcesService, Depends(get_sources_service)],
    episode_id: Annotated[int | None, Query(description="Filter by episode")] = None,
) -> list[SourceReleaseResponse]:
    """List persisted candidate releases for a work."""
    releases = service.list_releases_for_work(work_id=id, episode_id=episode_id)
    return [SourceReleaseResponse.model_validate(r) for r in releases]


# --- Download Tasks ---


@router.post(
    "/downloads",
    response_model=DownloadTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_download_task(
    request: DownloadTaskCreate,
    service: Annotated[SourcesService, Depends(get_sources_service)],
    start_immediately: Annotated[
        bool,
        Query(
            description="If false, queues the download for the background night scheduler."
        ),
    ] = True,
) -> DownloadTaskResponse:
    """Queue or start a new download task with Aria2."""
    task = service.create_download_task(request, start_immediately=start_immediately)
    return DownloadTaskResponse.model_validate(task)


@router.get("/downloads", response_model=list[DownloadTaskResponse])
def list_download_tasks(
    service: Annotated[SourcesService, Depends(get_sources_service)],
    status: Annotated[
        DownloadTaskStatus | None, Query(description="Filter by status")
    ] = None,
    library_item_id: Annotated[
        int | None, Query(description="Filter by library item")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DownloadTaskResponse]:
    """List active and historical download tasks."""
    tasks = service.list_tasks(
        status=status,
        library_item_id=library_item_id,
        limit=limit,
        offset=offset,
    )
    return [DownloadTaskResponse.model_validate(t) for t in tasks]


@router.get("/downloads/{id}", response_model=DownloadTaskResponse)
def get_download_task(
    id: int,
    service: Annotated[SourcesService, Depends(get_sources_service)],
) -> DownloadTaskResponse:
    """Retrieve status and metadata of a specific download task."""
    task = service.get_task(id)
    return DownloadTaskResponse.model_validate(task)


@router.post("/downloads/{id}/pause", response_model=DownloadTaskResponse)
def pause_download_task(
    id: int,
    service: Annotated[SourcesService, Depends(get_sources_service)],
) -> DownloadTaskResponse:
    """Pause an active download in Aria2."""
    task = service.pause_download(id)
    return DownloadTaskResponse.model_validate(task)


@router.post("/downloads/{id}/resume", response_model=DownloadTaskResponse)
def resume_download_task(
    id: int,
    service: Annotated[SourcesService, Depends(get_sources_service)],
) -> DownloadTaskResponse:
    """Resume a paused download or start a queued task in Aria2."""
    task = service.resume_download(id)
    return DownloadTaskResponse.model_validate(task)


@router.delete("/downloads/{id}", response_model=DownloadTaskResponse)
def cancel_download_task(
    id: int,
    service: Annotated[SourcesService, Depends(get_sources_service)],
) -> DownloadTaskResponse:
    """Cancel and remove a download task."""
    task = service.cancel_download(id)
    return DownloadTaskResponse.model_validate(task)


# --- Daemon Control & Stats ---


@router.get("/stats", response_model=Aria2StatsResponse)
def get_aria2_stats(
    service: Annotated[SourcesService, Depends(get_sources_service)],
) -> Aria2StatsResponse:
    """Fetch global download speeds and task counts from Aria2."""
    stats = service.get_aria2_stats()
    return Aria2StatsResponse(
        download_speed=stats.download_speed,
        upload_speed=stats.upload_speed,
        num_active=stats.num_active,
        num_waiting=stats.num_waiting,
        num_stopped=stats.num_stopped,
    )


@router.post("/speed-limit", status_code=status.HTTP_204_NO_CONTENT)
def set_speed_limit(
    request: SpeedLimitRequest,
    service: Annotated[SourcesService, Depends(get_sources_service)],
) -> Response:
    """Update global Aria2 download bandwidth limit in KB/s (0 = unlimited)."""
    service.set_speed_limit(request.max_download_limit_kb)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
