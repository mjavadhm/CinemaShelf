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


# -----------------------------------------------------------------------------
# Multi-Library & Storage Roots Schemas
# -----------------------------------------------------------------------------


class LibraryCreate(BaseModel):
    """Payload to create a new named library."""

    name: str = Field(..., min_length=1, max_length=255)
    content_type: str = "MOVIE"
    preferred_language: str = "fa"


class LibraryRootCreate(BaseModel):
    """Payload to add a storage root folder to a library."""

    label: str = Field(..., min_length=1, max_length=255)
    mount_path: str = Field(..., min_length=1, max_length=1000)


class LibraryRootResponse(BaseModel):
    """Details of a registered storage root."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    library_id: int
    label: str
    mount_path: str
    is_online: bool
    is_writable: bool
    used_bytes: int | None = 0
    total_bytes: int | None = 0
    last_scanned_at: datetime | None = None
    created_at: datetime


class LibraryResponse(BaseModel):
    """Response representing a named library collection."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    content_type: str
    default_download_root_id: int | None = None
    preferred_language: str
    roots: list[LibraryRootResponse] = Field(default_factory=list)
    movie_count: int = 0
    created_at: datetime


class ScanJobResponse(BaseModel):
    """Details and progress of a library filesystem scan."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    library_id: int
    root_id: int | None = None
    status: str
    files_discovered: int
    files_imported: int
    files_unmatched: int
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


# -----------------------------------------------------------------------------
# Server Filesystem Directory Browser Schemas
# -----------------------------------------------------------------------------


class DirectoryEntry(BaseModel):
    """Single directory item returned by server directory browser."""

    name: str
    path: str
    is_writable: bool
    has_subdirectories: bool = False


class DirectoryBrowseResponse(BaseModel):
    """Server filesystem directory listing response."""

    current_path: str
    parent_path: str | None = None
    is_writable: bool
    directories: list[DirectoryEntry] = Field(default_factory=list)
    total_bytes: int | None = None
    used_bytes: int | None = None
    free_bytes: int | None = None


class DirectorStat(BaseModel):
    """Director name and movie count in library."""

    name: str
    count: int


class MovieSummaryStat(BaseModel):
    """Minimal movie descriptor for statistics."""

    id: int
    title: str
    release_year: int | None = None


class LibraryStatsResponse(BaseModel):
    """Aggregated analytics and counters across library items."""

    total_movies: int
    total_files: int
    total_size_bytes: int
    average_rating: float
    top_directors: list[DirectorStat] = Field(default_factory=list)
    decade_distribution: dict[str, int] = Field(default_factory=dict)
    genre_distribution: dict[str, int] = Field(default_factory=dict)
    oldest_movie: MovieSummaryStat | None = None
    newest_movie: MovieSummaryStat | None = None


class CategorizeRequest(BaseModel):
    """Payload to generate virtual shortcut taxonomy."""

    destination_path: str
    library_id: int | None = None
    by_director: bool = True
    by_rating: bool = True
    by_decade: bool = True


class CategorizeResponse(BaseModel):
    """Result of virtual shortcut organization."""

    shortcuts_created: int
    categories: list[str]
    destination_path: str

