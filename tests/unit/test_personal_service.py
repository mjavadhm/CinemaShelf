"""Unit tests for PersonalService managing user state, diary logs, and shelves."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ApplicationError
from app.modules.metadata.models import MediaWork, WorkType
from app.modules.personal.models import WatchStatus
from app.modules.personal.schemas import (
    PersonalRecordUpdateRequest,
    WatchDiaryCreateRequest,
)
from app.modules.personal.service import PersonalService


@pytest.fixture
def sample_work(db_session: Session) -> MediaWork:
    """Fixture providing a sample movie."""
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=680,
        title="Pulp Fiction",
        release_year=1994,
    )
    db_session.add(work)
    db_session.commit()
    return work


@pytest.fixture
def sample_work_2(db_session: Session) -> MediaWork:
    """Fixture providing a second sample movie."""
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=550,
        title="Fight Club",
        release_year=1999,
    )
    db_session.add(work)
    db_session.commit()
    return work


def test_get_or_create_personal_record(
    db_session: Session, sample_work: MediaWork
) -> None:
    service = PersonalService(db_session)

    # First fetch creates default UNWATCHED record
    record = service.get_personal_record(sample_work.id)
    assert record.work_id == sample_work.id
    assert record.watch_status == WatchStatus.UNWATCHED
    assert record.in_watchlist is False
    assert record.is_favorite is False
    assert record.user_rating is None
    assert record.watch_count == 0

    # Non-existent work raises 404
    with pytest.raises(ApplicationError) as exc_info:
        service.get_personal_record(99999)
    assert exc_info.value.code == "work_not_found"


def test_update_personal_record(db_session: Session, sample_work: MediaWork) -> None:
    service = PersonalService(db_session)

    updated = service.update_personal_record(
        sample_work.id,
        PersonalRecordUpdateRequest(
            watch_status=WatchStatus.WATCHING,
            is_favorite=True,
            user_rating=9.5,
            personal_notes="Masterpiece dialogue.",
        ),
    )
    assert updated.watch_status == WatchStatus.WATCHING
    assert updated.is_favorite is True
    assert updated.user_rating == 9.5
    assert updated.personal_notes == "Masterpiece dialogue."


def test_toggle_watchlist_and_favorite(
    db_session: Session, sample_work: MediaWork
) -> None:
    service = PersonalService(db_session)

    # Toggle watchlist ON -> transitions UNWATCHED to WATCHLIST
    rec1 = service.toggle_watchlist(sample_work.id)
    assert rec1.in_watchlist is True
    assert rec1.watch_status == WatchStatus.WATCHLIST

    # Toggle watchlist OFF -> transitions back to UNWATCHED
    rec2 = service.toggle_watchlist(sample_work.id)
    assert rec2.in_watchlist is False
    assert rec2.watch_status == WatchStatus.UNWATCHED

    # Toggle favorite
    fav1 = service.toggle_favorite(sample_work.id)
    assert fav1.is_favorite is True
    fav2 = service.toggle_favorite(sample_work.id)
    assert fav2.is_favorite is False


def test_set_rating(db_session: Session, sample_work: MediaWork) -> None:
    service = PersonalService(db_session)

    rated = service.set_rating(sample_work.id, 8.5)
    assert rated.user_rating == 8.5

    cleared = service.set_rating(sample_work.id, None)
    assert cleared.user_rating is None


def test_diary_logging_and_record_synchronization(
    db_session: Session, sample_work: MediaWork
) -> None:
    service = PersonalService(db_session)

    # 1. Log first viewing
    view_date = date(2026, 5, 10)
    log1 = service.log_watch(
        WatchDiaryCreateRequest(
            work_id=sample_work.id,
            watched_date=view_date,
            rating_at_time=9.0,
            review_text="Incredible cinematography and script.",
            liked=True,
        )
    )
    assert log1.work_id == sample_work.id
    assert log1.rating_at_time == 9.0
    assert log1.liked is True

    record = service.get_personal_record(sample_work.id)
    assert record.watch_count == 1
    assert record.watch_status == WatchStatus.COMPLETED
    assert record.user_rating == 9.0
    assert record.is_favorite is True
    assert record.first_watched_at == view_date
    assert record.last_watched_at == view_date

    # 2. Log rewatch later
    rewatch_date = date(2026, 10, 1)
    log2 = service.log_watch(
        WatchDiaryCreateRequest(
            work_id=sample_work.id,
            watched_date=rewatch_date,
            is_rewatch=True,
            rating_at_time=9.5,
        )
    )
    assert log2.is_rewatch is True

    record = service.get_personal_record(sample_work.id)
    assert record.watch_count == 2
    assert record.first_watched_at == view_date
    assert record.last_watched_at == rewatch_date

    # 3. List diary entries
    diary_list = service.list_diary(work_id=sample_work.id)
    assert len(diary_list) == 2
    assert diary_list[0].id == log2.id

    # 4. Delete diary entry recalculates watch count
    service.delete_diary_entry(log2.id)
    record = service.get_personal_record(sample_work.id)
    assert record.watch_count == 1

    service.delete_diary_entry(log1.id)
    record = service.get_personal_record(sample_work.id)
    assert record.watch_count == 0
    assert record.watch_status == WatchStatus.UNWATCHED


def test_custom_shelf_lifecycle(
    db_session: Session, sample_work: MediaWork, sample_work_2: MediaWork
) -> None:
    service = PersonalService(db_session)

    # 1. Create shelf
    shelf1 = service.create_shelf(
        name="Top 90s Favorites",
        description="Best films of the nineties.",
    )
    assert shelf1.name == "Top 90s Favorites"
    assert shelf1.slug == "top-90s-favorites"
    assert shelf1.items_count == 0

    # 2. Duplicate shelf name rejection
    with pytest.raises(ApplicationError) as exc_info:
        service.create_shelf(name="Top 90s Favorites")
    assert exc_info.value.code == "shelf_name_exists"

    # 3. Slug collision disambiguation with distinct name
    shelf2 = service.create_shelf(name="Top: 90s Favorites")
    assert shelf2.slug == "top-90s-favorites-2"

    # 3. Add works to shelf
    item1 = service.add_to_shelf(
        shelf_id=shelf1.id,
        work_id=sample_work.id,
        rank_order=1,
        note="#1 Favorite",
    )
    assert item1.work_id == sample_work.id
    assert item1.work_title == "Pulp Fiction"
    assert item1.note == "#1 Favorite"

    item2 = service.add_to_shelf(
        shelf_id=shelf1.id,
        work_id=sample_work_2.id,
        rank_order=2,
    )
    assert item2.work_id == sample_work_2.id

    # 4. Fetch shelf detail
    detail = service.get_shelf(shelf1.slug)
    assert detail.items_count == 2
    assert len(detail.items) == 2
    assert detail.items[0].work_id == sample_work.id

    # 5. Reorder shelf
    reordered = service.reorder_shelf(shelf1.id, [sample_work_2.id, sample_work.id])
    assert reordered[0].work_id == sample_work_2.id
    assert reordered[0].rank_order == 1
    assert reordered[1].work_id == sample_work.id
    assert reordered[1].rank_order == 2

    # 6. Remove item from shelf
    service.remove_from_shelf(shelf1.id, sample_work.id)
    detail_after = service.get_shelf(shelf1.id)
    assert detail_after.items_count == 1

    # 7. Delete shelf
    service.delete_shelf(shelf1.id)
    with pytest.raises(ApplicationError) as exc_info:
        service.get_shelf(shelf1.id)
    assert exc_info.value.code == "shelf_not_found"


def test_catalog_filtering(
    db_session: Session, sample_work: MediaWork, sample_work_2: MediaWork
) -> None:
    service = PersonalService(db_session)

    # Set personal attributes
    service.update_personal_record(
        sample_work.id,
        PersonalRecordUpdateRequest(
            watch_status=WatchStatus.COMPLETED,
            is_favorite=True,
            user_rating=9.5,
        ),
    )
    service.update_personal_record(
        sample_work_2.id,
        PersonalRecordUpdateRequest(
            watch_status=WatchStatus.WATCHLIST,
            in_watchlist=True,
            is_favorite=False,
            user_rating=7.5,
        ),
    )

    # Filter by favorite
    favs = service.filter_catalog(is_favorite=True)
    assert len(favs) == 1
    assert favs[0].work_id == sample_work.id

    # Filter by min_rating
    high_rated = service.filter_catalog(min_rating=8.0)
    assert len(high_rated) == 1
    assert high_rated[0].work_id == sample_work.id

    # Filter by watchlist
    watchlist_items = service.filter_catalog(in_watchlist=True)
    assert len(watchlist_items) == 1
    assert watchlist_items[0].work_id == sample_work_2.id
