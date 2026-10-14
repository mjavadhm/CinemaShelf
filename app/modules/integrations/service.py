"""Application service and transaction orchestration for the integrations module."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.letterboxd import (
    LetterboxdClient,
    LetterboxdItem,
    LetterboxdItemType,
    LetterboxdPort,
)
from app.core.errors import ApplicationError
from app.modules.integrations.models import (
    ExternalItemMapping,
    IntegrationProvider,
    IntegrationSyncRun,
    SyncRunStatus,
)
from app.modules.integrations.repository import IntegrationsRepository
from app.modules.integrations.schemas import (
    ConflictPolicy,
    ImportSummaryResponse,
    RatingScaleMode,
    SyncRunResponse,
)
from app.modules.library.models import LibraryItem, LibraryItemStatus
from app.modules.metadata.models import MediaWork, WorkType
from app.modules.metadata.service import MetadataService
from app.modules.personal.models import (
    CustomShelf,
    ShelfItem,
    WatchDiaryLog,
    WatchStatus,
)
from app.modules.personal.schemas import WatchDiaryCreateRequest
from app.modules.personal.service import PersonalService, slugify

logger = logging.getLogger(__name__)


class IntegrationsService:
    """Service layer coordinating Letterboxd data ingestion, matching, and personal state updates."""

    def __init__(
        self,
        session: Session,
        letterboxd_client: LetterboxdPort | None = None,
        metadata_service: MetadataService | None = None,
        personal_service: PersonalService | None = None,
    ) -> None:
        self.session = session
        self.repository = IntegrationsRepository(session)
        self.letterboxd_client = letterboxd_client or LetterboxdClient()
        self.metadata_service = metadata_service or MetadataService(session)
        self.personal_service = personal_service or PersonalService(session)

    async def import_file(
        self,
        file_bytes: bytes,
        filename: str,
        conflict_policy: ConflictPolicy = ConflictPolicy.PRESERVE_LOCAL,
        scale_mode: RatingScaleMode = RatingScaleMode.RAW,
    ) -> ImportSummaryResponse:
        """Parse and synchronize a Letterboxd export ZIP archive or standalone CSV."""
        if not file_bytes:
            raise ApplicationError(
                code="empty_file",
                message="Uploaded file is empty",
                status_code=400,
            )

        lower_name = filename.lower()
        watchlist_count = 0
        ratings_count = 0
        watched_count = 0
        diary_count = 0
        lists_count = 0

        if lower_name.endswith(".zip"):
            try:
                archive = self.letterboxd_client.parse_zip_export(file_bytes)
            except ValueError as exc:
                raise ApplicationError(
                    code="invalid_zip_archive",
                    message=str(exc),
                    status_code=400,
                ) from exc

            items = archive.all_items
            watchlist_count = len(archive.watchlist)
            ratings_count = len(archive.ratings)
            watched_count = len(archive.watched)
            diary_count = len(archive.diary)
            lists_count = sum(len(lst) for lst in archive.lists.values())
            sync_type = "LETTERBOXD_ZIP_EXPORT"
        else:
            items = self.letterboxd_client.parse_csv(file_bytes, filename=filename)
            for it in items:
                if it.entry_type == LetterboxdItemType.WATCHLIST:
                    watchlist_count += 1
                elif it.entry_type == LetterboxdItemType.RATING:
                    ratings_count += 1
                elif it.entry_type == LetterboxdItemType.WATCHED:
                    watched_count += 1
                elif it.entry_type == LetterboxdItemType.DIARY:
                    diary_count += 1
                elif it.entry_type == LetterboxdItemType.LIST:
                    lists_count += 1
            sync_type = f"LETTERBOXD_CSV_{filename}"

        sync_run = self.repository.create_sync_run(
            provider=IntegrationProvider.LETTERBOXD,
            sync_type=sync_type,
        )
        self.session.commit()

        # Process parsed items
        items_processed = 0
        items_created = 0
        items_updated = 0
        items_failed = 0
        failed_errors: list[dict[str, Any]] = []

        for item in items:
            items_processed += 1
            try:
                work = await self._resolve_media_work(item)
                if not work:
                    items_failed += 1
                    failed_errors.append(
                        {
                            "title": item.title,
                            "year": item.release_year,
                            "error": "Could not match movie with local or external catalog",
                        }
                    )
                    continue

                is_created, is_updated = self._apply_item(
                    work=work,
                    item=item,
                    conflict_policy=conflict_policy,
                    scale_mode=scale_mode,
                )
                if is_created:
                    items_created += 1
                elif is_updated:
                    items_updated += 1

                self.session.flush()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Error syncing item '%s' (%s): %s",
                    item.title,
                    item.release_year,
                    exc,
                )
                items_failed += 1
                failed_errors.append(
                    {
                        "title": item.title,
                        "year": item.release_year,
                        "error": str(exc),
                    }
                )

        # Determine final status
        if items_failed == 0:
            final_status = SyncRunStatus.SUCCESS
        elif items_created + items_updated > 0:
            final_status = SyncRunStatus.PARTIAL
        else:
            final_status = SyncRunStatus.FAILED

        error_details = {"errors": failed_errors} if failed_errors else None
        finished_run = self.repository.finish_sync_run(
            run_id=sync_run.id,
            status=final_status,
            items_processed=items_processed,
            items_created=items_created,
            items_updated=items_updated,
            items_failed=items_failed,
            error_details=error_details,
        )
        self.session.commit()

        if finished_run is None:
            finished_run = sync_run

        msg = (
            f"Successfully processed {items_processed} items "
            f"({items_created} created, {items_updated} updated, {items_failed} failed)."
        )
        return ImportSummaryResponse(
            sync_run=SyncRunResponse.model_validate(finished_run),
            message=msg,
            total_items=items_processed,
            watchlist_count=watchlist_count,
            ratings_count=ratings_count,
            watched_count=watched_count,
            diary_count=diary_count,
            lists_count=lists_count,
        )

    async def _resolve_media_work(self, item: LetterboxdItem) -> MediaWork | None:
        """Resolve a LetterboxdItem to a MediaWork using cache mapping, local DB, or external search."""
        # 1. Check existing external URI mapping
        if item.letterboxd_uri:
            mapping = self.repository.get_external_mapping(
                IntegrationProvider.LETTERBOXD,
                item.letterboxd_uri,
            )
            if mapping:
                work = self.session.get(MediaWork, mapping.work_id)
                if work:
                    return work

        # 2. Check local database by title and optional year
        work = self.repository.find_work_by_title_year(item.title, item.release_year)
        if work:
            if item.letterboxd_uri:
                new_mapping = ExternalItemMapping(
                    provider=IntegrationProvider.LETTERBOXD,
                    external_key=item.letterboxd_uri,
                    work_id=work.id,
                    last_synced_at=datetime.now(UTC),
                )
                self.repository.save_external_mapping(new_mapping)
            return work

        # 3. External metadata search and ingest via TMDB
        try:
            candidates = await self.metadata_service.search_external(
                query=item.title,
                release_year=item.release_year,
                work_type=WorkType.MOVIE,
            )
            if candidates:
                chosen = candidates[0]
                for c in candidates:
                    if item.release_year and c.release_year == item.release_year:
                        chosen = c
                        break

                work = await self.metadata_service.get_or_ingest_work(
                    tmdb_id=chosen.tmdb_id,
                    work_type=WorkType.MOVIE,
                )
                if item.letterboxd_uri:
                    new_mapping = ExternalItemMapping(
                        provider=IntegrationProvider.LETTERBOXD,
                        external_key=item.letterboxd_uri,
                        work_id=work.id,
                        last_synced_at=datetime.now(UTC),
                    )
                    self.repository.save_external_mapping(new_mapping)
                return work
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "External metadata ingestion omitted for '%s' (%s): %s",
                item.title,
                item.release_year,
                exc,
            )

        return None

    def _apply_item(
        self,
        work: MediaWork,
        item: LetterboxdItem,
        conflict_policy: ConflictPolicy,
        scale_mode: RatingScaleMode,
    ) -> tuple[bool, bool]:
        """Apply Letterboxd record to personal state, returning (is_created, is_updated)."""
        is_created = False
        is_updated = False

        # 1. Watchlist handling
        if item.entry_type == LetterboxdItemType.WATCHLIST:
            # Ensure LibraryItem exists with status WANTED
            lib_stmt = select(LibraryItem).where(LibraryItem.work_id == work.id)
            lib_item = self.session.scalars(lib_stmt).first()
            if not lib_item:
                lib_item = LibraryItem(
                    work_id=work.id,
                    status=LibraryItemStatus.WANTED,
                    added_at=datetime.now(UTC),
                )
                self.session.add(lib_item)
                is_created = True

            record = self.personal_service.get_or_create_record(work.id)
            if not record.in_watchlist:
                record.in_watchlist = True
                is_updated = True
            if record.watch_status == WatchStatus.UNWATCHED:
                record.watch_status = WatchStatus.WATCHLIST
                is_updated = True

        # 2. Watched handling
        elif item.entry_type == LetterboxdItemType.WATCHED:
            record = self.personal_service.get_or_create_record(work.id)
            if record.watch_status != WatchStatus.COMPLETED:
                record.watch_status = WatchStatus.COMPLETED
                is_updated = True
            if record.watch_count == 0:
                record.watch_count = 1
                is_updated = True
            if item.watched_date:
                if (
                    not record.last_watched_at
                    or item.watched_date > record.last_watched_at
                ):
                    record.last_watched_at = item.watched_date
                    is_updated = True
                if (
                    not record.first_watched_at
                    or item.watched_date < record.first_watched_at
                ):
                    record.first_watched_at = item.watched_date
                    is_updated = True

        # 3. Rating handling
        elif item.entry_type == LetterboxdItemType.RATING:
            if item.rating is not None:
                record = self.personal_service.get_or_create_record(work.id)
                score = (
                    item.rating * 2.0
                    if scale_mode == RatingScaleMode.TEN_POINT
                    else item.rating
                )

                if (
                    conflict_policy == ConflictPolicy.PRESERVE_LOCAL
                    and record.user_rating is not None
                ):
                    pass  # Preserve local rating
                else:
                    if record.user_rating != score:
                        record.user_rating = score
                        is_updated = True

        # 4. Diary entry handling
        elif item.entry_type == LetterboxdItemType.DIARY:
            watched_d = item.watched_date or date.today()
            # Deduplicate diary entries on the same watched_date
            diary_stmt = select(WatchDiaryLog).where(
                WatchDiaryLog.work_id == work.id,
                WatchDiaryLog.watched_date == watched_d,
            )
            existing_diary = self.session.scalars(diary_stmt).first()
            if not existing_diary:
                diary_rating = item.rating
                if diary_rating is not None and scale_mode == RatingScaleMode.TEN_POINT:
                    diary_rating = diary_rating * 2.0

                req = WatchDiaryCreateRequest(
                    work_id=work.id,
                    watched_date=watched_d,
                    rating_at_time=diary_rating,
                    is_rewatch=item.is_rewatch,
                    review_text=item.review_text,
                )
                self.personal_service.log_watch(req)
                is_created = True

        # 5. Custom list handling
        elif item.entry_type == LetterboxdItemType.LIST and item.list_name:
            shelf_stmt = select(CustomShelf).where(CustomShelf.name == item.list_name)
            shelf = self.session.scalars(shelf_stmt).first()
            if not shelf:
                shelf = CustomShelf(
                    name=item.list_name,
                    slug=slugify(item.list_name),
                    description=f"Imported from Letterboxd list: {item.list_name}",
                )
                self.session.add(shelf)
                self.session.flush()

            item_stmt = select(ShelfItem).where(
                ShelfItem.shelf_id == shelf.id,
                ShelfItem.work_id == work.id,
            )
            existing_shelf_item = self.session.scalars(item_stmt).first()
            if not existing_shelf_item:
                shelf_item = ShelfItem(
                    shelf_id=shelf.id,
                    work_id=work.id,
                    rank_order=item.list_rank or 0,
                    note=item.review_text,
                    added_at=datetime.now(UTC),
                )
                self.session.add(shelf_item)
                is_created = True

        return is_created, is_updated

    def get_sync_run(self, run_id: int) -> IntegrationSyncRun | None:
        """Fetch a specific sync run by ID."""
        return self.repository.get_sync_run(run_id)

    def list_sync_runs(
        self,
        provider: IntegrationProvider | None = None,
        status: SyncRunStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[IntegrationSyncRun]:
        """List synchronization runs with optional status or provider filter."""
        return self.repository.list_sync_runs(
            provider=provider,
            status=status,
            limit=limit,
            offset=offset,
        )

    def list_mappings(
        self,
        provider: IntegrationProvider | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ExternalItemMapping]:
        """List stored external mappings."""
        return self.repository.list_mappings(
            provider=provider,
            limit=limit,
            offset=offset,
        )
