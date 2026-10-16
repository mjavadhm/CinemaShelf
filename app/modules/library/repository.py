"""Persistence queries for the library module (no internal commits)."""

from collections.abc import Sequence

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.modules.library.models import (
    Library,
    LibraryItem,
    LibraryItemStatus,
    LibraryMembership,
    LibraryRoot,
    MediaFile,
    ScanJob,
)
from app.modules.metadata.models import MediaWork
from app.modules.personal.models import PersonalRecord, WatchStatus


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

    def _build_items_query(
        self,
        status: LibraryItemStatus | None = None,
        library_id: int | None = None,
        search: str | None = None,
        genre: str | None = None,
        watch_status_filter: str | None = None,
        in_watchlist_filter: bool | None = None,
    ):
        stmt = select(LibraryItem).join(MediaWork, MediaWork.id == LibraryItem.work_id)
        stmt = stmt.outerjoin(PersonalRecord, PersonalRecord.work_id == MediaWork.id)

        if library_id is not None:
            stmt = stmt.join(
                LibraryMembership, LibraryMembership.work_id == LibraryItem.work_id
            ).where(LibraryMembership.library_id == library_id)

        if status:
            stmt = stmt.where(LibraryItem.status == status)

        if search:
            q = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(MediaWork.title).like(q),
                    func.lower(MediaWork.original_title).like(q),
                    func.lower(MediaWork.persian_title).like(q),
                    func.lower(MediaWork.imdb_id).like(q),
                )
            )

        if genre and genre != "ALL":
            from app.modules.metadata.models import Genre, WorkGenre

            stmt = (
                stmt.join(WorkGenre, WorkGenre.work_id == MediaWork.id)
                .join(Genre, Genre.id == WorkGenre.genre_id)
                .where(
                    or_(
                        Genre.name == genre,
                        Genre.persian_name == genre,
                    )
                )
            )

        if watch_status_filter:
            norm_watch = watch_status_filter.strip().upper()
            if norm_watch == "WATCHED":
                stmt = stmt.where(
                    or_(
                        PersonalRecord.watch_status.in_(
                            [WatchStatus.COMPLETED, WatchStatus.WATCHING]
                        ),
                        PersonalRecord.watch_count > 0,
                        PersonalRecord.user_rating.is_not(None),
                    )
                )
            elif norm_watch == "UNWATCHED":
                stmt = stmt.where(
                    or_(
                        PersonalRecord.id.is_(None),
                        and_(
                            PersonalRecord.watch_status.notin_(
                                [WatchStatus.COMPLETED, WatchStatus.WATCHING]
                            ),
                            or_(
                                PersonalRecord.watch_count == 0,
                                PersonalRecord.watch_count.is_(None),
                            ),
                            PersonalRecord.user_rating.is_(None),
                        ),
                    )
                )

        if in_watchlist_filter is not None:
            if in_watchlist_filter:
                stmt = stmt.where(PersonalRecord.in_watchlist.is_(True))
            else:
                stmt = stmt.where(
                    or_(
                        PersonalRecord.id.is_(None),
                        PersonalRecord.in_watchlist.is_(False),
                    )
                )

        return stmt

    def list_items(
        self,
        status: LibraryItemStatus | None = None,
        library_id: int | None = None,
        search: str | None = None,
        genre: str | None = None,
        watch_status_filter: str | None = None,
        in_watchlist_filter: bool | None = None,
        sort_by: str = "added_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[LibraryItem]:
        """List library items with filtering and multi-attribute sorting."""
        stmt = (
            self._build_items_query(
                status=status,
                library_id=library_id,
                search=search,
                genre=genre,
                watch_status_filter=watch_status_filter,
                in_watchlist_filter=in_watchlist_filter,
            )
            .options(
                joinedload(LibraryItem.work).joinedload(MediaWork.personal_record),
                selectinload(LibraryItem.media_files),
            )
        )

        is_asc = sort_order.strip().lower() == "asc"

        sort_col_map = {
            "imdb_rating": MediaWork.imdb_rating,
            "user_rating": PersonalRecord.user_rating,
            "tmdb_rating": MediaWork.tmdb_rating,
            "runtime": MediaWork.runtime_minutes,
            "release_year": MediaWork.release_year,
            "title": func.lower(MediaWork.title),
            "added_at": LibraryItem.added_at,
        }

        col = sort_col_map.get(sort_by.lower(), LibraryItem.added_at)

        if is_asc:
            stmt = stmt.order_by(col.asc().nulls_last(), LibraryItem.id.asc())
        else:
            stmt = stmt.order_by(col.desc().nulls_last(), LibraryItem.id.desc())

        stmt = stmt.limit(limit).offset(offset)
        return self.session.scalars(stmt).unique().all()

    def count_items(
        self,
        status: LibraryItemStatus | None = None,
        library_id: int | None = None,
        search: str | None = None,
        genre: str | None = None,
        watch_status_filter: str | None = None,
        in_watchlist_filter: bool | None = None,
    ) -> int:
        """Count total library items matching query filters."""
        stmt = self._build_items_query(
            status=status,
            library_id=library_id,
            search=search,
            genre=genre,
            watch_status_filter=watch_status_filter,
            in_watchlist_filter=in_watchlist_filter,
        )
        subq = stmt.subquery()
        count_stmt = select(func.count()).select_from(subq)
        return self.session.scalar(count_stmt) or 0

    def get_all_media_files(self) -> Sequence[MediaFile]:
        """Fetch all registered media files across all items."""
        return self.session.scalars(select(MediaFile)).all()

    def get_all_root_folders(self) -> Sequence[str]:
        """Fetch distinct non-null root folder paths."""
        stmt = (
            select(LibraryItem.root_folder_path)
            .where(LibraryItem.root_folder_path.is_not(None))
            .distinct()
        )
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

    # -------------------------------------------------------------------------
    # Multi-Library Persistence
    # -------------------------------------------------------------------------

    def create_library(self, library: Library) -> Library:
        """Persist a new Library collection."""
        self.session.add(library)
        self.session.flush()
        return library

    def get_library_by_id(self, library_id: int) -> Library | None:
        """Fetch Library by ID eagerly loading roots and memberships."""
        stmt = (
            select(Library)
            .where(Library.id == library_id)
            .options(
                selectinload(Library.roots),
                selectinload(Library.memberships),
            )
        )
        return self.session.scalars(stmt).first()

    def get_library_by_name(self, name: str) -> Library | None:
        """Fetch Library by unique name."""
        stmt = select(Library).where(Library.name == name)
        return self.session.scalars(stmt).first()

    def list_libraries(self) -> Sequence[Library]:
        """List all libraries with their configured roots."""
        stmt = select(Library).options(
            selectinload(Library.roots),
            selectinload(Library.memberships),
        ).order_by(Library.id.asc())
        return self.session.scalars(stmt).all()

    def delete_library(self, library: Library) -> None:
        """Delete a library entity and cascade."""
        self.session.delete(library)
        self.session.flush()

    # -------------------------------------------------------------------------
    # Library Roots Persistence
    # -------------------------------------------------------------------------

    def create_root(self, root: LibraryRoot) -> LibraryRoot:
        """Persist a new storage root folder."""
        self.session.add(root)
        self.session.flush()
        return root

    def get_root_by_id(self, root_id: int) -> LibraryRoot | None:
        """Fetch storage root by ID."""
        return self.session.get(LibraryRoot, root_id)

    def get_root_by_path(self, mount_path: str) -> LibraryRoot | None:
        """Fetch storage root by mount path."""
        stmt = select(LibraryRoot).where(LibraryRoot.mount_path == mount_path)
        return self.session.scalars(stmt).first()

    def list_roots_for_library(self, library_id: int) -> Sequence[LibraryRoot]:
        """Fetch all roots belonging to a specific library."""
        stmt = select(LibraryRoot).where(LibraryRoot.library_id == library_id).order_by(LibraryRoot.id.asc())
        return self.session.scalars(stmt).all()

    def list_all_roots(self) -> Sequence[LibraryRoot]:
        """Fetch all configured storage roots across all libraries."""
        stmt = select(LibraryRoot).order_by(LibraryRoot.id.asc())
        return self.session.scalars(stmt).all()

    def delete_root(self, root: LibraryRoot) -> None:
        """Delete a storage root folder."""
        self.session.delete(root)
        self.session.flush()

    # -------------------------------------------------------------------------
    # Scan Jobs Persistence
    # -------------------------------------------------------------------------

    def create_scan_job(self, job: ScanJob) -> ScanJob:
        """Record a new filesystem scan execution."""
        self.session.add(job)
        self.session.flush()
        return job

    def get_scan_job_by_id(self, job_id: int) -> ScanJob | None:
        """Retrieve scan job by ID."""
        return self.session.get(ScanJob, job_id)

    def list_scan_jobs(self, library_id: int | None = None, limit: int = 20) -> Sequence[ScanJob]:
        """List recent scan jobs."""
        stmt = select(ScanJob).order_by(ScanJob.started_at.desc()).limit(limit)
        if library_id:
            stmt = stmt.where(ScanJob.library_id == library_id)
        return self.session.scalars(stmt).all()

