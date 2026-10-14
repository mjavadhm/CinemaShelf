"""Unit tests for IntegrationsService coordinating Letterboxd file sync."""

import io
import zipfile
from datetime import date
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApplicationError
from app.modules.integrations.models import (
    ExternalItemMapping,
    SyncRunStatus,
)
from app.modules.integrations.schemas import ConflictPolicy, RatingScaleMode
from app.modules.integrations.service import IntegrationsService
from app.modules.library.models import LibraryItem, LibraryItemStatus
from app.modules.metadata.models import MediaWork, WorkType
from app.modules.metadata.service import MetadataService
from app.modules.personal.models import (
    CustomShelf,
    PersonalRecord,
    ShelfItem,
    WatchDiaryLog,
    WatchStatus,
)


@pytest.fixture
def sample_work_1(db_session: Session) -> MediaWork:
    """Fixture providing Children of Men."""
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=9693,
        title="Children of Men",
        release_year=2006,
    )
    db_session.add(work)
    db_session.commit()
    return work


@pytest.fixture
def sample_work_2(db_session: Session) -> MediaWork:
    """Fixture providing Ex Machina."""
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=264660,
        title="Ex Machina",
        release_year=2014,
    )
    db_session.add(work)
    db_session.commit()
    return work


@pytest.fixture
def mock_meta_service(db_session: Session) -> MetadataService:
    """Mock metadata service that returns empty candidates for unknowns."""
    mock = AsyncMock(spec=MetadataService)
    mock.search_external.return_value = []
    return mock


@pytest.mark.asyncio
async def test_import_watchlist_creates_wanted_and_updates_personal(
    db_session: Session,
    sample_work_1: MediaWork,
) -> None:
    service = IntegrationsService(db_session)
    csv_text = """Date,Name,Year,Letterboxd URI
2024-01-15,Children of Men,2006,https://boxd.it/29pC
"""
    result = await service.import_file(
        file_bytes=csv_text.encode("utf-8"),
        filename="watchlist.csv",
    )

    assert result.total_items == 1
    assert result.watchlist_count == 1
    assert result.sync_run.status == SyncRunStatus.SUCCESS

    # Verify LibraryItem created as WANTED
    lib_stmt = select(LibraryItem).where(LibraryItem.work_id == sample_work_1.id)
    lib_item = db_session.scalars(lib_stmt).first()
    assert lib_item is not None
    assert lib_item.status == LibraryItemStatus.WANTED

    # Verify PersonalRecord marked in_watchlist
    rec_stmt = select(PersonalRecord).where(PersonalRecord.work_id == sample_work_1.id)
    record = db_session.scalars(rec_stmt).first()
    assert record is not None
    assert record.in_watchlist is True
    assert record.watch_status == WatchStatus.WATCHLIST

    # Verify ExternalItemMapping saved
    map_stmt = select(ExternalItemMapping).where(
        ExternalItemMapping.external_key == "https://boxd.it/29pC"
    )
    mapping = db_session.scalars(map_stmt).first()
    assert mapping is not None
    assert mapping.work_id == sample_work_1.id


@pytest.mark.asyncio
async def test_import_ratings_with_conflict_policies_and_scale(
    db_session: Session,
    sample_work_2: MediaWork,
) -> None:
    service = IntegrationsService(db_session)

    # Pre-set local rating
    record = PersonalRecord(
        work_id=sample_work_2.id,
        user_rating=9.5,
        watch_status=WatchStatus.COMPLETED,
    )
    db_session.add(record)
    db_session.commit()

    csv_text = """Date,Name,Year,Letterboxd URI,Rating
2024-02-01,Ex Machina,2014,https://boxd.it/70zS,4.0
"""

    # 1. PRESERVE_LOCAL: local 9.5 must not be overwritten
    res_preserve = await service.import_file(
        file_bytes=csv_text.encode("utf-8"),
        filename="ratings.csv",
        conflict_policy=ConflictPolicy.PRESERVE_LOCAL,
    )
    assert res_preserve.sync_run.status == SyncRunStatus.SUCCESS

    db_session.refresh(record)
    assert record.user_rating == 9.5

    # 2. OVERWRITE_LOCAL with TEN_POINT: 4.0 * 2 = 8.0
    res_overwrite = await service.import_file(
        file_bytes=csv_text.encode("utf-8"),
        filename="ratings.csv",
        conflict_policy=ConflictPolicy.OVERWRITE_LOCAL,
        scale_mode=RatingScaleMode.TEN_POINT,
    )
    assert res_overwrite.sync_run.status == SyncRunStatus.SUCCESS

    db_session.refresh(record)
    assert record.user_rating == 8.0


@pytest.mark.asyncio
async def test_import_diary_deduplication(
    db_session: Session,
    sample_work_1: MediaWork,
) -> None:
    service = IntegrationsService(db_session)
    csv_text = """Date,Name,Year,Letterboxd URI,Rating,Rewatch,Tags,Watched Date
2024-03-01,Children of Men,2006,https://boxd.it/29pC,5.0,No,"sci-fi",2024-02-28
"""
    # First import
    res1 = await service.import_file(
        file_bytes=csv_text.encode("utf-8"),
        filename="diary.csv",
    )
    assert res1.sync_run.status == SyncRunStatus.SUCCESS
    assert res1.diary_count == 1

    logs_stmt = select(WatchDiaryLog).where(WatchDiaryLog.work_id == sample_work_1.id)
    logs = list(db_session.scalars(logs_stmt).all())
    assert len(logs) == 1
    assert logs[0].watched_date == date(2024, 2, 28)
    assert logs[0].rating_at_time == 5.0

    # Second import (same file / date) -> must not duplicate diary log
    res2 = await service.import_file(
        file_bytes=csv_text.encode("utf-8"),
        filename="diary.csv",
    )
    assert res2.sync_run.status == SyncRunStatus.SUCCESS
    logs_after = list(db_session.scalars(logs_stmt).all())
    assert len(logs_after) == 1


@pytest.mark.asyncio
async def test_import_custom_list(
    db_session: Session,
    sample_work_1: MediaWork,
    sample_work_2: MediaWork,
) -> None:
    service = IntegrationsService(db_session)
    csv_text = """Position,Name,Year,URL,Description
1,Children of Men,2006,https://boxd.it/29pC,Masterpiece
2,Ex Machina,2014,https://boxd.it/70zS,Tense AI thriller
"""
    res = await service.import_file(
        file_bytes=csv_text.encode("utf-8"),
        filename="top-dystopia.csv",
    )
    assert res.sync_run.status == SyncRunStatus.SUCCESS

    # Verify shelf creation
    shelf_stmt = select(CustomShelf).where(CustomShelf.name == "Top Dystopia")
    shelf = db_session.scalars(shelf_stmt).first()
    assert shelf is not None

    items_stmt = select(ShelfItem).where(ShelfItem.shelf_id == shelf.id)
    items = list(db_session.scalars(items_stmt).all())
    assert len(items) == 2


@pytest.mark.asyncio
async def test_import_full_zip_archive(
    db_session: Session,
    sample_work_1: MediaWork,
    sample_work_2: MediaWork,
) -> None:
    service = IntegrationsService(db_session)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr(
            "watchlist.csv",
            "Date,Name,Year,Letterboxd URI\n2024-01-01,Children of Men,2006,https://boxd.it/29pC\n",
        )
        zf.writestr(
            "watched.csv",
            "Date,Name,Year,Letterboxd URI\n2024-01-02,Ex Machina,2014,https://boxd.it/70zS\n",
        )

    res = await service.import_file(
        file_bytes=zip_buffer.getvalue(),
        filename="letterboxd-export.zip",
    )
    assert res.sync_run.status == SyncRunStatus.SUCCESS
    assert res.total_items == 2
    assert res.watchlist_count == 1
    assert res.watched_count == 1


@pytest.mark.asyncio
async def test_import_unmatched_work_records_failure(
    db_session: Session,
    sample_work_1: MediaWork,
    mock_meta_service: MetadataService,
) -> None:
    service = IntegrationsService(db_session, metadata_service=mock_meta_service)
    csv_text = """Date,Name,Year,Letterboxd URI
2024-01-01,Children of Men,2006,https://boxd.it/29pC
2024-01-02,Some Unknown Obscure Film,1931,https://boxd.it/9999
"""
    res = await service.import_file(
        file_bytes=csv_text.encode("utf-8"),
        filename="watchlist.csv",
    )
    # 1 success + 1 failure = PARTIAL status
    assert res.sync_run.status == SyncRunStatus.PARTIAL
    assert res.sync_run.items_processed == 2
    assert res.sync_run.items_failed == 1
    assert res.sync_run.error_details is not None
    assert len(res.sync_run.error_details["errors"]) == 1


@pytest.mark.asyncio
async def test_import_empty_file_raises_error(db_session: Session) -> None:
    service = IntegrationsService(db_session)
    with pytest.raises(ApplicationError) as exc_info:
        await service.import_file(b"", filename="empty.csv")
    assert exc_info.value.code == "empty_file"
