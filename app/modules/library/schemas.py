"""Pydantic DTOs and API contracts for the library module."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.library.models import LibraryItemStatus
from app.modules.metadata.models import WorkType
from app.modules.metadata.schemas import MediaWorkSummaryResponse


class MediaFileCreate(BaseModel):
    """Schema for adding a media file to a library item."""

    file_path: str
    file_name: str
    file_size_bytes: int | None = None
    resolution: str | None = None
    video_codec: str | None = None
    source_type: str | None = None
    audio_languages: list[str] | None = None
    subtitle_paths: list[str] | None = None
    has_soft_sub: bool = False
    episode_id: int | None = None


class MediaFileResponse(BaseModel):
    """Schema for returning media file details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    library_item_id: int
    episode_id: int | None = None
    file_path: str
    file_name: str
    file_size_bytes: int | None = None
    resolution: str | None = None
    video_codec: str | None = None
    source_type: str | None = None
    audio_languages: list[str] | None = None
    subtitle_paths: list[str] | None = None
    has_soft_sub: bool = False
    is_missing: bool = False
    is_online: bool = False
    last_verified_at: datetime | None = None
    created_at: datetime


class StorageVolumeResponse(BaseModel):
    """Storage drive/volume status schema."""

    id: str
    label: str
    mount_path: str
    used_bytes: int
    total_bytes: int
    is_online: bool


class PersonalSummary(BaseModel):
    """Compact personal status for library listings."""

    model_config = ConfigDict(from_attributes=True)

    user_rating: float | None = None
    in_watchlist: bool = False
    is_favorite: bool = False
    watch_status: str | None = None
    last_watched_at: datetime | None = None


class LibraryItemCreate(BaseModel):
    """Schema for creating a library item either via work_id or tmdb_id."""

    work_id: int | None = Field(default=None, description="Existing MediaWork ID")
    tmdb_id: int | None = Field(
        default=None, description="TMDB ID to fetch automatically"
    )
    work_type: WorkType = WorkType.MOVIE
    status: LibraryItemStatus = LibraryItemStatus.WANTED
    root_folder_path: str | None = None


class LibraryItemStatusUpdate(BaseModel):
    """Schema for changing the status of a library item."""

    status: LibraryItemStatus


class LibraryItemSummaryResponse(BaseModel):
    """Summary of a library item for listings."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    work_id: int
    status: LibraryItemStatus
    root_folder_path: str | None = None
    added_at: datetime
    work: MediaWorkSummaryResponse
    media_files: list[MediaFileResponse] = Field(default_factory=list)
    personal_record: PersonalSummary | None = None


class LibraryItemDetailResponse(BaseModel):
    """Detailed view of a library item with files."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    work_id: int
    status: LibraryItemStatus
    root_folder_path: str | None = None
    added_at: datetime
    work: MediaWorkSummaryResponse
    media_files: list[MediaFileResponse] = Field(default_factory=list)
    personal_record: PersonalSummary | None = None
