"""Pydantic DTOs and API contracts for the personal module."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.personal.models import WatchStatus


class PersonalRecordResponse(BaseModel):
    """API response model for a user's personal record on a media work."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    work_id: int
    watch_status: WatchStatus
    in_watchlist: bool
    is_favorite: bool
    user_rating: float | None = None
    watch_count: int = 0
    personal_notes: str | None = None
    first_watched_at: date | None = None
    last_watched_at: date | None = None
    created_at: datetime
    updated_at: datetime


class PersonalRecordUpdateRequest(BaseModel):
    """Payload to update fields of a personal record."""

    watch_status: WatchStatus | None = None
    in_watchlist: bool | None = None
    is_favorite: bool | None = None
    user_rating: float | None = Field(default=None, ge=0.0, le=10.0)
    personal_notes: str | None = None


class WatchlistToggleRequest(BaseModel):
    """Explicit or toggle request for watchlist status."""

    in_watchlist: bool | None = None


class FavoriteToggleRequest(BaseModel):
    """Explicit or toggle request for favorite status."""

    is_favorite: bool | None = None


class RatingRequest(BaseModel):
    """Payload to set or clear user rating."""

    rating: float | None = Field(default=None, ge=0.0, le=10.0)


class WatchDiaryCreateRequest(BaseModel):
    """Payload to log a viewing event in the watch diary."""

    work_id: int
    episode_id: int | None = None
    watched_date: date = Field(default_factory=date.today)
    rating_at_time: float | None = Field(default=None, ge=0.0, le=10.0)
    is_rewatch: bool = False
    review_text: str | None = None
    liked: bool = False


class WatchDiaryLogResponse(BaseModel):
    """API response for an individual watch diary event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    work_id: int
    episode_id: int | None = None
    watched_date: date
    rating_at_time: float | None = None
    is_rewatch: bool = False
    review_text: str | None = None
    liked: bool = False
    created_at: datetime


class CustomShelfCreateRequest(BaseModel):
    """Payload to create a new custom shelf collection."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_smart_shelf: bool = False


class CustomShelfUpdateRequest(BaseModel):
    """Payload to update an existing custom shelf."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class ShelfItemCreateRequest(BaseModel):
    """Payload to add a media work into a custom shelf."""

    work_id: int
    rank_order: int = 0
    note: str | None = None


class ShelfItemResponse(BaseModel):
    """API response model for an item inside a custom shelf."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    shelf_id: int
    work_id: int
    rank_order: int
    note: str | None = None
    added_at: datetime
    work_title: str | None = None
    work_release_year: int | None = None
    work_poster_path: str | None = None


class CustomShelfResponse(BaseModel):
    """API response model for a custom shelf summary."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None = None
    is_smart_shelf: bool = False
    items_count: int = 0
    created_at: datetime


class CustomShelfDetailResponse(BaseModel):
    """API response model for a custom shelf including member items."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None = None
    is_smart_shelf: bool = False
    items_count: int = 0
    created_at: datetime
    items: list[ShelfItemResponse] = []


class ShelfReorderRequest(BaseModel):
    """Payload to reorder items inside a shelf."""

    work_ids: list[int] = Field(min_length=1)


class PersonalWorkCatalogItem(BaseModel):
    """Item response when querying catalog works with personal attributes."""

    work_id: int
    title: str
    original_title: str | None = None
    release_year: int | None = None
    poster_path: str | None = None
    tmdb_rating: float | None = None
    imdb_rating: float | None = None
    personal: PersonalRecordResponse | None = None
