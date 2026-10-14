"""SQLAlchemy ORM models owned by the metadata module."""

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.integrations.models import ExternalItemMapping
    from app.modules.library.models import LibraryItem
    from app.modules.personal.models import PersonalRecord, ShelfItem, WatchDiaryLog
    from app.modules.playback.models import PlaybackProgress
    from app.modules.sources.models import SourceRelease


class WorkType(str, enum.Enum):
    """Media work distinction between movie and tv show."""

    MOVIE = "MOVIE"
    SHOW = "SHOW"


class CreditType(str, enum.Enum):
    """Credit participation category."""

    CAST = "CAST"
    CREW = "CREW"


class MediaWork(Base, TimestampMixin):
    """Foundational media catalog work entity."""

    __tablename__ = "media_works"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_type: Mapped[WorkType] = mapped_column(
        Enum(WorkType, name="work_type_enum"),
        index=True,
        nullable=False,
    )
    tmdb_id: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, nullable=False
    )
    imdb_id: Mapped[str | None] = mapped_column(
        String(32), unique=True, index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    original_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    persian_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    release_year: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    backdrop_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tmdb_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    tmdb_vote_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imdb_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    imdb_votes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rotten_tomatoes_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metascore: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships within metadata
    genres: Mapped[list["Genre"]] = relationship(
        "Genre",
        secondary="work_genres",
        back_populates="works",
        lazy="selectin",
        viewonly=True,
    )
    work_genres: Mapped[list["WorkGenre"]] = relationship(
        "WorkGenre",
        back_populates="work",
        cascade="all, delete-orphan",
        overlaps="genres",
    )
    credits: Mapped[list["WorkCredit"]] = relationship(
        "WorkCredit",
        back_populates="work",
        cascade="all, delete-orphan",
    )
    seasons: Mapped[list["MediaSeason"]] = relationship(
        "MediaSeason",
        back_populates="work",
        cascade="all, delete-orphan",
    )
    episodes: Mapped[list["MediaEpisode"]] = relationship(
        "MediaEpisode",
        back_populates="work",
        cascade="all, delete-orphan",
    )

    # Cross-module relationships
    library_item: Mapped["LibraryItem | None"] = relationship(
        "LibraryItem",
        back_populates="work",
        uselist=False,
        cascade="all, delete-orphan",
    )
    source_releases: Mapped[list["SourceRelease"]] = relationship(
        "SourceRelease",
        back_populates="work",
        cascade="all, delete-orphan",
    )
    playback_progresses: Mapped[list["PlaybackProgress"]] = relationship(
        "PlaybackProgress",
        back_populates="work",
        cascade="all, delete-orphan",
    )
    personal_record: Mapped["PersonalRecord | None"] = relationship(
        "PersonalRecord",
        back_populates="work",
        uselist=False,
        cascade="all, delete-orphan",
    )
    watch_diary_logs: Mapped[list["WatchDiaryLog"]] = relationship(
        "WatchDiaryLog",
        back_populates="work",
        cascade="all, delete-orphan",
    )
    shelf_items: Mapped[list["ShelfItem"]] = relationship(
        "ShelfItem",
        back_populates="work",
        cascade="all, delete-orphan",
    )
    external_mappings: Mapped[list["ExternalItemMapping"]] = relationship(
        "ExternalItemMapping",
        back_populates="work",
        cascade="all, delete-orphan",
    )


class Genre(Base, TimestampMixin):
    """Standardized media genre classification."""

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tmdb_genre_id: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    persian_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    works: Mapped[list["MediaWork"]] = relationship(
        "MediaWork",
        secondary="work_genres",
        back_populates="genres",
        viewonly=True,
    )


class WorkGenre(Base, TimestampMixin):
    """Many-to-many link between media work and genre."""

    __tablename__ = "work_genres"
    __table_args__ = (
        UniqueConstraint("work_id", "genre_id", name="uq_work_genres_work_genre"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        ForeignKey("media_works.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    genre_id: Mapped[int] = mapped_column(
        ForeignKey("genres.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    work: Mapped["MediaWork"] = relationship(
        "MediaWork", back_populates="work_genres", overlaps="genres,works"
    )
    genre: Mapped["Genre"] = relationship("Genre", overlaps="genres,works")


class Person(Base, TimestampMixin):
    """Individual involved in media production (cast or crew)."""

    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tmdb_person_id: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, nullable=False
    )
    imdb_person_id: Mapped[str | None] = mapped_column(
        String(32), unique=True, index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    persian_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    known_for_department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    credits: Mapped[list["WorkCredit"]] = relationship(
        "WorkCredit",
        back_populates="person",
        cascade="all, delete-orphan",
    )


class WorkCredit(Base, TimestampMixin):
    """Cast or crew credit linking a person to a media work."""

    __tablename__ = "work_credits"
    __table_args__ = (
        Index(
            "ix_work_credits_person_credit_type_job", "person_id", "credit_type", "job"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        ForeignKey("media_works.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tmdb_credit_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, index=True, nullable=True
    )
    credit_type: Mapped[CreditType] = mapped_column(
        Enum(CreditType, name="credit_type_enum"),
        index=True,
        nullable=False,
    )
    department: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    job: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    character_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    billing_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    work: Mapped["MediaWork"] = relationship("MediaWork", back_populates="credits")
    person: Mapped["Person"] = relationship("Person", back_populates="credits")


class MediaSeason(Base, TimestampMixin):
    """TV show season belonging to a media work."""

    __tablename__ = "media_seasons"
    __table_args__ = (
        UniqueConstraint(
            "work_id", "season_number", name="uq_media_seasons_work_season"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        ForeignKey("media_works.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tmdb_season_id: Mapped[int | None] = mapped_column(
        Integer, unique=True, nullable=True
    )
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    air_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    episode_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    work: Mapped["MediaWork"] = relationship("MediaWork", back_populates="seasons")
    episodes: Mapped[list["MediaEpisode"]] = relationship(
        "MediaEpisode",
        back_populates="season",
        cascade="all, delete-orphan",
    )


class MediaEpisode(Base, TimestampMixin):
    """Single episode within a season and media work."""

    __tablename__ = "media_episodes"
    __table_args__ = (
        UniqueConstraint(
            "work_id",
            "season_number",
            "episode_number",
            name="uq_media_episodes_work_season_ep",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        ForeignKey("media_works.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    season_id: Mapped[int] = mapped_column(
        ForeignKey("media_seasons.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tmdb_episode_id: Mapped[int | None] = mapped_column(
        Integer, unique=True, nullable=True
    )
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    air_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    still_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tmdb_rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    work: Mapped["MediaWork"] = relationship("MediaWork", back_populates="episodes")
    season: Mapped["MediaSeason"] = relationship(
        "MediaSeason", back_populates="episodes"
    )
