"""Pydantic DTOs and API contracts for the metadata module."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.metadata.models import CreditType, WorkType


class GenreResponse(BaseModel):
    """Genre schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tmdb_genre_id: int
    name: str
    persian_name: str | None = None


class PersonResponse(BaseModel):
    """Person representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tmdb_person_id: int
    name: str
    original_name: str | None = None
    persian_name: str | None = None
    known_for_department: str | None = None
    profile_path: str | None = None


class WorkCreditResponse(BaseModel):
    """Cast or crew credit details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    person: PersonResponse
    credit_type: CreditType
    department: str
    job: str
    character_name: str | None = None
    billing_order: int | None = None


class MediaEpisodeResponse(BaseModel):
    """TV episode schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    season_number: int
    episode_number: int
    title: str | None = None
    overview: str | None = None
    air_date: date | None = None
    runtime_minutes: int | None = None
    still_path: str | None = None
    tmdb_rating: float | None = None


class MediaSeasonResponse(BaseModel):
    """TV season schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    season_number: int
    title: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    air_date: date | None = None
    episode_count: int | None = None
    episodes: list[MediaEpisodeResponse] = Field(default_factory=list)


class MediaWorkSummaryResponse(BaseModel):
    """Summary of MediaWork for listings."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    work_type: WorkType
    tmdb_id: int
    imdb_id: str | None = None
    title: str
    original_title: str | None = None
    persian_title: str | None = None
    release_date: date | None = None
    release_year: int | None = None
    runtime_minutes: int | None = None
    status: str | None = None
    poster_path: str | None = None
    tmdb_rating: float | None = None
    imdb_rating: float | None = None
    rotten_tomatoes_score: int | None = None
    metascore: int | None = None


class MediaWorkDetailResponse(MediaWorkSummaryResponse):
    """Detailed MediaWork including genres, credits, and seasons."""

    original_language: str | None = None
    overview: str | None = None
    backdrop_path: str | None = None
    tmdb_vote_count: int | None = None
    imdb_votes: int | None = None
    last_synced_at: datetime | None = None

    genres: list[GenreResponse] = Field(default_factory=list)
    credits: list[WorkCreditResponse] = Field(default_factory=list)
    seasons: list[MediaSeasonResponse] = Field(default_factory=list)


class ExternalSearchResultResponse(BaseModel):
    """External metadata search result candidate."""

    tmdb_id: int
    title: str
    work_type: WorkType
    original_title: str | None = None
    release_year: int | None = None
    overview: str | None = None
    poster_path: str | None = None
    vote_average: float | None = None


class IngestWorkRequest(BaseModel):
    """Request to ingest or refresh a work from TMDB."""

    tmdb_id: int
    work_type: WorkType = WorkType.MOVIE
