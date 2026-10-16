"""Pydantic DTOs and API contracts for the integrations module."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.modules.integrations.models import IntegrationProvider, SyncRunStatus


class ConflictPolicy(StrEnum):
    """Policy for resolving conflicts between incoming Letterboxd data and local data."""

    PRESERVE_LOCAL = "PRESERVE_LOCAL"
    OVERWRITE_LOCAL = "OVERWRITE_LOCAL"


class RatingScaleMode(StrEnum):
    """Conversion mode for Letterboxd 5-star ratings."""

    RAW = "RAW"  # Preserves the exact 0.5 - 5.0 score
    TEN_POINT = "TEN_POINT"  # Multiplies by 2 to map to a 1.0 - 10.0 scale


class SyncRunResponse(BaseModel):
    """API response model for an integration sync execution audit record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: IntegrationProvider
    sync_type: str
    status: SyncRunStatus
    items_processed: int
    items_created: int
    items_updated: int
    items_failed: int
    started_at: datetime
    finished_at: datetime | None = None
    error_details: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ExternalItemMappingResponse(BaseModel):
    """API response model for mapping an external identifier to a MediaWork."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: IntegrationProvider
    external_key: str
    work_id: int
    last_synced_hash: str | None = None
    last_synced_at: datetime
    created_at: datetime
    updated_at: datetime


class ImportSummaryResponse(BaseModel):
    """High-level summary response returned after an import batch completes."""

    sync_run: SyncRunResponse
    message: str
    total_items: int
    watchlist_count: int = 0
    ratings_count: int = 0
    watched_count: int = 0
    diary_count: int = 0
    lists_count: int = 0


class LetterboxdLocalSyncRequest(BaseModel):
    """Request model for synchronizing from saved local HTML files."""

    folder_path: str = "for scraping"
    conflict_policy: ConflictPolicy = ConflictPolicy.PRESERVE_LOCAL
    scale_mode: RatingScaleMode = RatingScaleMode.TEN_POINT


class LetterboxdBrowserSyncRequest(BaseModel):
    """Request model for automated multi-page browser scraping."""

    username: str
    include_watchlist: bool = True
    max_pages: int = 20
    conflict_policy: ConflictPolicy = ConflictPolicy.PRESERVE_LOCAL
    scale_mode: RatingScaleMode = RatingScaleMode.TEN_POINT


class LetterboxdRateRequest(BaseModel):
    """Request model for auto-rating a movie on Letterboxd."""

    work_id: int
    rating: int  # 1-10 scale


class LetterboxdRateResponse(BaseModel):
    """Response model for Letterboxd rating submission."""

    work_id: int
    title: str
    rating: int
    success: bool
    message: str
