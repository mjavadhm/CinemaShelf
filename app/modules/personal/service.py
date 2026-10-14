"""Application service and transaction orchestration for the personal module."""

import re
import unicodedata

from sqlalchemy.orm import Session

from app.core.errors import ApplicationError
from app.modules.metadata.repository import MetadataRepository
from app.modules.personal.models import (
    CustomShelf,
    PersonalRecord,
    ShelfItem,
    WatchDiaryLog,
    WatchStatus,
)
from app.modules.personal.repository import PersonalRepository
from app.modules.personal.schemas import (
    CustomShelfDetailResponse,
    CustomShelfResponse,
    PersonalRecordResponse,
    PersonalRecordUpdateRequest,
    PersonalWorkCatalogItem,
    ShelfItemResponse,
    WatchDiaryCreateRequest,
    WatchDiaryLogResponse,
)


def slugify(value: str) -> str:
    """Generate a clean, URL-friendly slug supporting Latin, numerals, and dashes."""
    value = unicodedata.normalize("NFKD", value)
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value or "shelf"


class PersonalService:
    """Service layer coordinating personal domain rules and transactions."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = PersonalRepository(session)
        self.metadata_repo = MetadataRepository(session)

    # -------------------------------------------------------------------------
    # PersonalRecord Management
    # -------------------------------------------------------------------------

    def get_or_create_record(self, work_id: int) -> PersonalRecord:
        """Fetch existing PersonalRecord or instantiate a new default record."""
        work = self.metadata_repo.get_work_by_id(work_id)
        if work is None:
            raise ApplicationError(
                code="work_not_found",
                message=f"MediaWork {work_id} not found",
                status_code=404,
            )

        record = self.repository.get_personal_record(work_id)
        if record is None:
            record = PersonalRecord(
                work_id=work_id,
                watch_status=WatchStatus.UNWATCHED,
                in_watchlist=False,
                is_favorite=False,
                watch_count=0,
            )
            self.repository.save_personal_record(record)
        return record

    def get_personal_record(self, work_id: int) -> PersonalRecordResponse:
        """Get the personal record associated with a work."""
        record = self.get_or_create_record(work_id)
        self.session.commit()
        return PersonalRecordResponse.model_validate(record)

    def update_personal_record(
        self, work_id: int, req: PersonalRecordUpdateRequest
    ) -> PersonalRecordResponse:
        """Update user watch status, rating, favorite, or personal notes."""
        record = self.get_or_create_record(work_id)

        if req.watch_status is not None:
            record.watch_status = req.watch_status
        if req.in_watchlist is not None:
            record.in_watchlist = req.in_watchlist
            if req.in_watchlist and record.watch_status == WatchStatus.UNWATCHED:
                record.watch_status = WatchStatus.WATCHLIST
        if req.is_favorite is not None:
            record.is_favorite = req.is_favorite
        if req.user_rating is not None:
            record.user_rating = req.user_rating
        if req.personal_notes is not None:
            record.personal_notes = req.personal_notes

        self.repository.save_personal_record(record)
        self.session.commit()
        return PersonalRecordResponse.model_validate(record)

    def toggle_watchlist(
        self, work_id: int, state: bool | None = None
    ) -> PersonalRecordResponse:
        """Toggle or set watchlist status for a work."""
        record = self.get_or_create_record(work_id)
        new_state = (not record.in_watchlist) if state is None else state
        record.in_watchlist = new_state

        if new_state and record.watch_status == WatchStatus.UNWATCHED:
            record.watch_status = WatchStatus.WATCHLIST
        elif not new_state and record.watch_status == WatchStatus.WATCHLIST:
            record.watch_status = WatchStatus.UNWATCHED

        self.repository.save_personal_record(record)
        self.session.commit()
        return PersonalRecordResponse.model_validate(record)

    def toggle_favorite(
        self, work_id: int, state: bool | None = None
    ) -> PersonalRecordResponse:
        """Toggle or set favorite status for a work."""
        record = self.get_or_create_record(work_id)
        new_state = (not record.is_favorite) if state is None else state
        record.is_favorite = new_state

        self.repository.save_personal_record(record)
        self.session.commit()
        return PersonalRecordResponse.model_validate(record)

    def set_rating(self, work_id: int, rating: float | None) -> PersonalRecordResponse:
        """Set or clear the user rating for a work."""
        record = self.get_or_create_record(work_id)
        record.user_rating = rating

        self.repository.save_personal_record(record)
        self.session.commit()
        return PersonalRecordResponse.model_validate(record)

    # -------------------------------------------------------------------------
    # Watch Diary
    # -------------------------------------------------------------------------

    def log_watch(self, req: WatchDiaryCreateRequest) -> WatchDiaryLogResponse:
        """Log an event in the watch diary and update the work's personal record."""
        work = self.metadata_repo.get_work_by_id(req.work_id)
        if work is None:
            raise ApplicationError(
                code="work_not_found",
                message=f"MediaWork {req.work_id} not found",
                status_code=404,
            )

        log = WatchDiaryLog(
            work_id=req.work_id,
            episode_id=req.episode_id,
            watched_date=req.watched_date,
            rating_at_time=req.rating_at_time,
            is_rewatch=req.is_rewatch,
            review_text=req.review_text,
            liked=req.liked,
        )
        self.repository.create_diary_log(log)

        # Synchronize personal record
        record = self.get_or_create_record(req.work_id)
        record.watch_count += 1
        if (
            record.first_watched_at is None
            or req.watched_date < record.first_watched_at
        ):
            record.first_watched_at = req.watched_date
        if record.last_watched_at is None or req.watched_date > record.last_watched_at:
            record.last_watched_at = req.watched_date

        if record.watch_status in (
            WatchStatus.UNWATCHED,
            WatchStatus.WATCHLIST,
            WatchStatus.WATCHING,
        ):
            record.watch_status = WatchStatus.COMPLETED

        if req.rating_at_time is not None and record.user_rating is None:
            record.user_rating = req.rating_at_time

        if req.liked:
            record.is_favorite = True

        self.repository.save_personal_record(record)
        self.session.commit()
        return WatchDiaryLogResponse.model_validate(log)

    def list_diary(
        self, work_id: int | None = None, limit: int = 50, offset: int = 0
    ) -> list[WatchDiaryLogResponse]:
        """List diary logs with optional work filtering and pagination."""
        logs = self.repository.list_diary_logs(
            work_id=work_id, limit=limit, offset=offset
        )
        return [WatchDiaryLogResponse.model_validate(l) for l in logs]

    def get_diary_entry(self, log_id: int) -> WatchDiaryLogResponse:
        """Fetch an individual diary entry by ID."""
        log = self.repository.get_diary_log(log_id)
        if log is None:
            raise ApplicationError(
                code="diary_log_not_found",
                message=f"Diary entry {log_id} not found",
                status_code=404,
            )
        return WatchDiaryLogResponse.model_validate(log)

    def delete_diary_entry(self, log_id: int) -> bool:
        """Delete an individual diary entry and recalculate record watch count."""
        log = self.repository.get_diary_log(log_id)
        if log is None:
            raise ApplicationError(
                code="diary_log_not_found",
                message=f"Diary entry {log_id} not found",
                status_code=404,
            )

        work_id = log.work_id
        self.repository.delete_diary_log(log)

        # Recalculate watch count
        remaining_count = self.repository.count_diary_logs_for_work(work_id)
        record = self.repository.get_personal_record(work_id)
        if record is not None:
            record.watch_count = remaining_count
            if remaining_count == 0 and record.watch_status == WatchStatus.COMPLETED:
                record.watch_status = WatchStatus.UNWATCHED
            self.repository.save_personal_record(record)

        self.session.commit()
        return True

    # -------------------------------------------------------------------------
    # Custom Shelves
    # -------------------------------------------------------------------------

    def create_shelf(
        self,
        name: str,
        description: str | None = None,
        is_smart_shelf: bool = False,
    ) -> CustomShelfResponse:
        """Create a new custom shelf with an auto-generated unique slug."""
        existing_name = self.repository.get_shelf_by_name(name)
        if existing_name is not None:
            raise ApplicationError(
                code="shelf_name_exists",
                message=f"A shelf named '{name}' already exists",
                status_code=409,
            )

        base_slug = slugify(name)
        slug = base_slug
        counter = 2
        while self.repository.get_shelf_by_slug(slug) is not None:
            slug = f"{base_slug}-{counter}"
            counter += 1

        shelf = CustomShelf(
            name=name,
            slug=slug,
            description=description,
            is_smart_shelf=is_smart_shelf,
        )
        self.repository.create_shelf(shelf)
        self.session.commit()
        return CustomShelfResponse(
            id=shelf.id,
            name=shelf.name,
            slug=shelf.slug,
            description=shelf.description,
            is_smart_shelf=shelf.is_smart_shelf,
            items_count=0,
            created_at=shelf.created_at,
        )

    def list_shelves(self) -> list[CustomShelfResponse]:
        """List all custom shelves with their member item counts."""
        results = self.repository.list_shelves()
        return [
            CustomShelfResponse(
                id=shelf.id,
                name=shelf.name,
                slug=shelf.slug,
                description=shelf.description,
                is_smart_shelf=shelf.is_smart_shelf,
                items_count=count,
                created_at=shelf.created_at,
            )
            for shelf, count in results
        ]

    def get_shelf(self, shelf_id_or_slug: int | str) -> CustomShelfDetailResponse:
        """Fetch shelf details and loaded items by ID or slug."""
        if isinstance(shelf_id_or_slug, int) or (
            isinstance(shelf_id_or_slug, str) and shelf_id_or_slug.isdigit()
        ):
            shelf = self.repository.get_shelf_by_id(int(shelf_id_or_slug))
        else:
            shelf = self.repository.get_shelf_by_slug(str(shelf_id_or_slug))

        if shelf is None:
            raise ApplicationError(
                code="shelf_not_found",
                message=f"Custom shelf '{shelf_id_or_slug}' not found",
                status_code=404,
            )

        items = self.repository.get_shelf_items(shelf.id)
        item_dtos = [
            ShelfItemResponse(
                id=item.id,
                shelf_id=item.shelf_id,
                work_id=item.work_id,
                rank_order=item.rank_order,
                note=item.note,
                added_at=item.added_at,
                work_title=item.work.title if item.work else None,
                work_release_year=item.work.release_year if item.work else None,
                work_poster_path=item.work.poster_path if item.work else None,
            )
            for item in items
        ]

        return CustomShelfDetailResponse(
            id=shelf.id,
            name=shelf.name,
            slug=shelf.slug,
            description=shelf.description,
            is_smart_shelf=shelf.is_smart_shelf,
            items_count=len(item_dtos),
            created_at=shelf.created_at,
            items=item_dtos,
        )

    def update_shelf(
        self,
        shelf_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> CustomShelfResponse:
        """Update a custom shelf's name or description."""
        shelf = self.repository.get_shelf_by_id(shelf_id)
        if shelf is None:
            raise ApplicationError(
                code="shelf_not_found",
                message=f"Custom shelf {shelf_id} not found",
                status_code=404,
            )

        if name is not None and name != shelf.name:
            existing_name = self.repository.get_shelf_by_name(name)
            if existing_name is not None and existing_name.id != shelf.id:
                raise ApplicationError(
                    code="shelf_name_exists",
                    message=f"A shelf named '{name}' already exists",
                    status_code=409,
                )
            shelf.name = name
            base_slug = slugify(name)
            slug = base_slug
            counter = 2
            existing = self.repository.get_shelf_by_slug(slug)
            while existing is not None and existing.id != shelf.id:
                slug = f"{base_slug}-{counter}"
                counter += 1
                existing = self.repository.get_shelf_by_slug(slug)
            shelf.slug = slug

        if description is not None:
            shelf.description = description

        items_count = len(self.repository.get_shelf_items(shelf.id))
        self.session.commit()
        return CustomShelfResponse(
            id=shelf.id,
            name=shelf.name,
            slug=shelf.slug,
            description=shelf.description,
            is_smart_shelf=shelf.is_smart_shelf,
            items_count=items_count,
            created_at=shelf.created_at,
        )

    def delete_shelf(self, shelf_id: int) -> bool:
        """Delete a custom shelf and its member items."""
        shelf = self.repository.get_shelf_by_id(shelf_id)
        if shelf is None:
            raise ApplicationError(
                code="shelf_not_found",
                message=f"Custom shelf {shelf_id} not found",
                status_code=404,
            )
        self.repository.delete_shelf(shelf)
        self.session.commit()
        return True

    def add_to_shelf(
        self,
        shelf_id: int,
        work_id: int,
        rank_order: int = 0,
        note: str | None = None,
    ) -> ShelfItemResponse:
        """Add or update a work in a custom shelf."""
        shelf = self.repository.get_shelf_by_id(shelf_id)
        if shelf is None:
            raise ApplicationError(
                code="shelf_not_found",
                message=f"Custom shelf {shelf_id} not found",
                status_code=404,
            )

        work = self.metadata_repo.get_work_by_id(work_id)
        if work is None:
            raise ApplicationError(
                code="work_not_found",
                message=f"MediaWork {work_id} not found",
                status_code=404,
            )

        item = self.repository.get_shelf_item(shelf_id, work_id)
        if item is not None:
            item.rank_order = rank_order
            if note is not None:
                item.note = note
        else:
            item = ShelfItem(
                shelf_id=shelf_id,
                work_id=work_id,
                rank_order=rank_order,
                note=note,
            )
            self.repository.add_shelf_item(item)

        self.session.commit()
        return ShelfItemResponse(
            id=item.id,
            shelf_id=item.shelf_id,
            work_id=item.work_id,
            rank_order=item.rank_order,
            note=item.note,
            added_at=item.added_at,
            work_title=work.title,
            work_release_year=work.release_year,
            work_poster_path=work.poster_path,
        )

    def remove_from_shelf(self, shelf_id: int, work_id: int) -> bool:
        """Remove a work from a custom shelf."""
        item = self.repository.get_shelf_item(shelf_id, work_id)
        if item is None:
            raise ApplicationError(
                code="shelf_item_not_found",
                message=f"Work {work_id} not found in shelf {shelf_id}",
                status_code=404,
            )
        self.repository.remove_shelf_item(item)
        self.session.commit()
        return True

    def reorder_shelf(
        self, shelf_id: int, work_ids: list[int]
    ) -> list[ShelfItemResponse]:
        """Reorder items in a shelf according to a provided work ID list."""
        shelf = self.repository.get_shelf_by_id(shelf_id)
        if shelf is None:
            raise ApplicationError(
                code="shelf_not_found",
                message=f"Custom shelf {shelf_id} not found",
                status_code=404,
            )

        for index, wid in enumerate(work_ids, start=1):
            item = self.repository.get_shelf_item(shelf_id, wid)
            if item is not None:
                item.rank_order = index

        self.session.commit()
        return self.get_shelf(shelf_id).items

    # -------------------------------------------------------------------------
    # Catalog Filtering
    # -------------------------------------------------------------------------

    def filter_catalog(
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
    ) -> list[PersonalWorkCatalogItem]:
        """Filter library works by personal user criteria."""
        results = self.repository.filter_personal_works(
            watch_status=watch_status,
            in_watchlist=in_watchlist,
            is_favorite=is_favorite,
            min_rating=min_rating,
            max_rating=max_rating,
            shelf_id=shelf_id,
            genre_id=genre_id,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )

        return [
            PersonalWorkCatalogItem(
                work_id=work.id,
                title=work.title,
                original_title=work.original_title,
                release_year=work.release_year,
                poster_path=work.poster_path,
                tmdb_rating=work.tmdb_rating,
                imdb_rating=work.imdb_rating,
                personal=(
                    PersonalRecordResponse.model_validate(record)
                    if record is not None
                    else None
                ),
            )
            for work, record in results
        ]
