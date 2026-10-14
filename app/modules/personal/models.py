"""SQLAlchemy ORM models owned by the personal module."""

import enum
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.metadata.models import MediaEpisode, MediaWork


class WatchStatus(str, enum.Enum):
    """Overall watch status of a media work for the user."""

    UNWATCHED = "UNWATCHED"
    WATCHLIST = "WATCHLIST"
    WATCHING = "WATCHING"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"
    DROPPED = "DROPPED"


class PersonalRecord(Base, TimestampMixin):
    """Personal watch status, rating, and notes associated with a MediaWork."""

    __tablename__ = "personal_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        ForeignKey("media_works.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    watch_status: Mapped[WatchStatus] = mapped_column(
        Enum(WatchStatus, name="watch_status_enum"),
        index=True,
        nullable=False,
        default=WatchStatus.UNWATCHED,
    )
    in_watchlist: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )
    user_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    watch_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    personal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_watched_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_watched_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    work: Mapped["MediaWork"] = relationship(
        "MediaWork", back_populates="personal_record"
    )


class WatchDiaryLog(Base, TimestampMixin):
    """Individual diary event of viewing a work or episode."""

    __tablename__ = "watch_diary_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        ForeignKey("media_works.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    episode_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_episodes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    watched_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    rating_at_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_rewatch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    liked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    work: Mapped["MediaWork"] = relationship(
        "MediaWork", back_populates="watch_diary_logs"
    )
    episode: Mapped["MediaEpisode | None"] = relationship("MediaEpisode")


class CustomShelf(Base, TimestampMixin):
    """User-curated collection or smart shelf for organizing works."""

    __tablename__ = "custom_shelves"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_smart_shelf: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    items: Mapped[list["ShelfItem"]] = relationship(
        "ShelfItem",
        back_populates="shelf",
        cascade="all, delete-orphan",
    )


class ShelfItem(Base, TimestampMixin):
    """Membership mapping a work into a custom shelf."""

    __tablename__ = "shelf_items"
    __table_args__ = (
        UniqueConstraint("shelf_id", "work_id", name="uq_shelf_items_shelf_work"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shelf_id: Mapped[int] = mapped_column(
        ForeignKey("custom_shelves.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    work_id: Mapped[int] = mapped_column(
        ForeignKey("media_works.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    rank_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    shelf: Mapped["CustomShelf"] = relationship("CustomShelf", back_populates="items")
    work: Mapped["MediaWork"] = relationship("MediaWork", back_populates="shelf_items")
