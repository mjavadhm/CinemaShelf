"""Pydantic DTOs and API contracts for the sources module."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.sources.models import DownloadTaskStatus, ReleaseProvider


class SourceReleaseBase(BaseModel):
    """Base fields for a discovered or manual release."""

    work_id: int
    episode_id: int | None = None
    provider: ReleaseProvider = ReleaseProvider.MANUAL
    source_page_url: str | None = None
    download_url: str
    quality_label: str | None = None
    resolution: str | None = None
    encoder: str | None = None
    size_text: str | None = None
    size_bytes: int | None = None
    is_dubbed: bool = False
    has_persian_sub: bool = False


class SourceReleaseCreate(SourceReleaseBase):
    """Payload to create or manually register a source release."""


class SourceReleaseResponse(SourceReleaseBase):
    """API representation of a source release."""

    id: int
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DownloadTaskCreate(BaseModel):
    """Payload to schedule or initiate a download task."""

    library_item_id: int
    release_id: int | None = None
    episode_id: int | None = None
    download_url: str | None = None
    destination_dir: str | None = None
    file_name: str | None = None


class DownloadTaskResponse(BaseModel):
    """API representation of an active or completed download task."""

    id: int
    library_item_id: int
    episode_id: int | None = None
    release_id: int | None = None
    aria2_gid: str | None = None
    download_url: str
    destination_dir: str
    file_name: str | None = None
    status: DownloadTaskStatus
    total_bytes: int | None = None
    downloaded_bytes: int = 0
    progress_percent: float = 0.0
    download_speed_bps: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpeedLimitRequest(BaseModel):
    """Payload to adjust global Aria2 download bandwidth."""

    max_download_limit_kb: int = Field(
        ...,
        ge=0,
        description="Speed limit in KB/s. 0 means unlimited.",
    )


class Aria2StatsResponse(BaseModel):
    """Aria2 daemon global stats representation."""

    is_online: bool = True
    download_speed: int
    upload_speed: int
    num_active: int
    num_waiting: int
    num_stopped: int


class DiscoverReleasesResponse(BaseModel):
    """Result of scraping releases for a movie or episode."""

    work_id: int
    source_page_url: str | None = None
    total_found: int
    releases: list[SourceReleaseResponse]
