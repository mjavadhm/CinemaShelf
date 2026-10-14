"""Persistence queries for the personal module (no internal commits)."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.modules.metadata.models import MediaWork, WorkGenre
from app.modules.personal.models import (
    CustomShelf,
    PersonalRecord,
    ShelfItem,
    WatchDiaryLog,
    WatchStatus,
)


class PersonalRepository:
    """Repository for personal persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # -------------------------------------------------------------------------
    # PersonalRecord
    # -------------------------------------------------------------------------

    def get_personal_record(self, work_id: int) -> PersonalRecord | None:
        """Fetch a personal record by media work ID."""
        stmt = select(PersonalRecord).where(PersonalRecord.work_id == work_id)
        return self.session.scalars(stmt).first()

    def save_personal_record(self, record: PersonalRecord) -> PersonalRecord:
        """Save or update a personal record."""
        self.session.add(record)
        self.session.flush()
        return record

    # -------------------------------------------------------------------------
    # WatchDiaryLog
    # -------------------------------------------------------------------------

    def create_diary_log(self, log: WatchDiaryLog) -> WatchDiaryLog:
        """Create a new watch diary log entry."""
        self.session.add(log)
        self.session.flush()
        return log

    def get_diary_log(self, log_id: int) -> WatchDiaryLog | None:
        """Fetch an individual diary log by ID."""
        return self.session.get(WatchDiaryLog, log_id)

    def list_diary_logs(
        self,
        work_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[WatchDiaryLog]:
        """List diary logs with optional work filtering and pagination."""
        stmt = select(WatchDiaryLog)
        if work_id is not None:
            stmt = stmt.where(WatchDiaryLog.work_id == work_id)

        stmt = (
            stmt.order_by(
                WatchDiaryLog.watched_date.desc(),
                WatchDiaryLog.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        return self.session.scalars(stmt).all()

    def delete_diary_log(self, log: WatchDiaryLog) -> None:
        """Delete an individual diary log entry."""
        self.session.delete(log)
        self.session.flush()

    def count_diary_logs_for_work(self, work_id: int) -> int:
        """Count total diary logs recorded for a given work."""
        stmt = select(func.count(WatchDiaryLog.id)).where(
            WatchDiaryLog.work_id == work_id
        )
        return self.session.scalar(stmt) or 0

    # -------------------------------------------------------------------------
    # CustomShelf & ShelfItem
    # -------------------------------------------------------------------------

    def create_shelf(self, shelf: CustomShelf) -> CustomShelf:
        """Create a new custom shelf."""
        self.session.add(shelf)
        self.session.flush()
        return shelf

    def get_shelf_by_id(self, shelf_id: int) -> CustomShelf | None:
        """Fetch a custom shelf by its ID."""
        return self.session.get(CustomShelf, shelf_id)

    def get_shelf_by_name(self, name: str) -> CustomShelf | None:
        """Fetch a custom shelf by its unique name."""
        stmt = select(CustomShelf).where(CustomShelf.name == name)
        return self.session.scalars(stmt).first()

    def get_shelf_by_slug(self, slug: str) -> CustomShelf | None:
        """Fetch a custom shelf by its unique slug."""
        stmt = select(CustomShelf).where(CustomShelf.slug == slug)
        return self.session.scalars(stmt).first()

    def list_shelves(self) -> Sequence[tuple[CustomShelf, int]]:
        """List all custom shelves paired with their member item counts."""
        stmt = (
            select(CustomShelf, func.count(ShelfItem.id).label("items_count"))
            .outerjoin(ShelfItem, ShelfItem.shelf_id == CustomShelf.id)
            .group_by(CustomShelf.id)
            .order_by(CustomShelf.name.asc())
        )
        return self.session.execute(stmt).all()  # type: ignore[return-value]

    def delete_shelf(self, shelf: CustomShelf) -> None:
        """Delete a custom shelf and its cascade members."""
        self.session.delete(shelf)
        self.session.flush()

    def add_shelf_item(self, item: ShelfItem) -> ShelfItem:
        """Add or save a work item into a custom shelf."""
        self.session.add(item)
        self.session.flush()
        return item

    def get_shelf_item(self, shelf_id: int, work_id: int) -> ShelfItem | None:
        """Fetch an individual item in a shelf by shelf ID and work ID."""
        stmt = select(ShelfItem).where(
            ShelfItem.shelf_id == shelf_id,
            ShelfItem.work_id == work_id,
        )
        return self.session.scalars(stmt).first()

    def remove_shelf_item(self, item: ShelfItem) -> None:
        """Remove an item from a shelf."""
        self.session.delete(item)
        self.session.flush()

    def get_shelf_items(self, shelf_id: int) -> Sequence[ShelfItem]:
        """Fetch all member items in a shelf with loaded work details."""
        stmt = (
            select(ShelfItem)
            .options(joinedload(ShelfItem.work))
            .where(ShelfItem.shelf_id == shelf_id)
            .order_by(ShelfItem.rank_order.asc(), ShelfItem.added_at.desc())
        )
        return self.session.scalars(stmt).all()

    # -------------------------------------------------------------------------
    # Personal Catalog Filtering
    # -------------------------------------------------------------------------

    def filter_personal_works(
        self,
        watch_status: WatchStatus | None = None,
        in_watchlist: bool | None = None,
        is_favorite: bool | None = None,
        min_rating: float | None = None,
        max_rating: float | None = None,
        shelf_id: int | None = None,
        genre_id: int | None = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[tuple[MediaWork, PersonalRecord | None]]:
        """Filter media works joined with their personal records."""
        # Base query joining MediaWork with optional PersonalRecord
        stmt = select(MediaWork, PersonalRecord).outerjoin(
            PersonalRecord, PersonalRecord.work_id == MediaWork.id
        )

        if shelf_id is not None:
            stmt = stmt.join(ShelfItem, ShelfItem.work_id == MediaWork.id).where(
                ShelfItem.shelf_id == shelf_id
            )

        if genre_id is not None:
            stmt = stmt.join(WorkGenre, WorkGenre.work_id == MediaWork.id).where(
                WorkGenre.genre_id == genre_id
            )

        if watch_status is not None:
            stmt = stmt.where(PersonalRecord.watch_status == watch_status)

        if in_watchlist is not None:
            stmt = stmt.where(PersonalRecord.in_watchlist == in_watchlist)

        if is_favorite is not None:
            stmt = stmt.where(PersonalRecord.is_favorite == is_favorite)

        if min_rating is not None:
            stmt = stmt.where(PersonalRecord.user_rating >= min_rating)

        if max_rating is not None:
            stmt = stmt.where(PersonalRecord.user_rating <= max_rating)

        # Sorting logic
        order_col: Any = PersonalRecord.updated_at
        if sort_by == "rating":
            order_col = PersonalRecord.user_rating
        elif sort_by == "last_watched":
            order_col = PersonalRecord.last_watched_at
        elif sort_by == "title":
            order_col = MediaWork.title
        elif sort_by == "release_year":
            order_col = MediaWork.release_year

        if sort_order.lower() == "asc":
            stmt = stmt.order_by(order_col.asc().nulls_last())
        else:
            stmt = stmt.order_by(order_col.desc().nulls_last())

        stmt = stmt.offset(offset).limit(limit)
        return self.session.execute(stmt).all()  # type: ignore[return-value]
