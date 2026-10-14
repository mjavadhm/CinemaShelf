"""Persistence queries for the library module (no internal commits)."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.modules.library.models import LibraryItem, LibraryItemStatus, MediaFile


class LibraryRepository:
    """Repository for library persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_item_by_id(self, item_id: int) -> LibraryItem | None:
        """Fetch LibraryItem by ID with work and media files eagerly loaded."""
        stmt = (
            select(LibraryItem)
            .where(LibraryItem.id == item_id)
            .options(
                joinedload(LibraryItem.work),
                selectinload(LibraryItem.media_files),
            )
        )
        return self.session.scalars(stmt).first()

    def get_item_by_work_id(self, work_id: int) -> LibraryItem | None:
        """Fetch LibraryItem by associated MediaWork ID."""
        stmt = (
            select(LibraryItem)
            .where(LibraryItem.work_id == work_id)
            .options(
                joinedload(LibraryItem.work),
                selectinload(LibraryItem.media_files),
            )
        )
        return self.session.scalars(stmt).first()

    def list_items(
        self,
        status: LibraryItemStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[LibraryItem]:
        """List library items with optional status filtering."""
        stmt = (
            select(LibraryItem)
            .options(joinedload(LibraryItem.work))
            .order_by(LibraryItem.added_at.desc())
        )
        if status:
            stmt = stmt.where(LibraryItem.status == status)

        stmt = stmt.limit(limit).offset(offset)
        return self.session.scalars(stmt).all()

    def create_item(self, item: LibraryItem) -> LibraryItem:
        """Add a new LibraryItem to the session."""
        self.session.add(item)
        self.session.flush()
        return item

    def delete_item(self, item: LibraryItem) -> None:
        """Delete a LibraryItem from the session."""
        self.session.delete(item)
        self.session.flush()

    def add_media_file(self, media_file: MediaFile) -> MediaFile:
        """Add a physical MediaFile to the session."""
        self.session.add(media_file)
        self.session.flush()
        return media_file

    def get_media_file_by_path(self, file_path: str) -> MediaFile | None:
        """Fetch MediaFile by its unique path."""
        stmt = select(MediaFile).where(MediaFile.file_path == file_path)
        return self.session.scalars(stmt).first()

    def get_media_file_by_id(self, file_id: int) -> MediaFile | None:
        """Fetch MediaFile by ID."""
        return self.session.get(MediaFile, file_id)
