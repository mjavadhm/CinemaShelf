"""Pydantic DTOs and API contracts for the playback module."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileAccessResponse(BaseModel):
    """Result of requesting an OS file or directory open action."""

    media_file_id: int | None = None
    work_id: int | None = None
    path: str
    action: str
    success: bool


class WatchStatusResponse(BaseModel):
    """Current watched state of a film or episode."""

    work_id: int
    episode_id: int | None = None
    is_watched: bool
    last_watched_at: datetime | None = None


class WatchedWorkItemResponse(BaseModel):
    """Detailed record of a media work's watch status."""

    id: int
    work_id: int
    episode_id: int | None = None
    media_file_id: int | None = None
    is_completed: bool
    last_watched_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
