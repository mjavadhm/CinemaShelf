"""Integration tests for CinemaShelf SQLAlchemy 2.0 ORM models and constraints."""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.integrations.models import (
    ExternalItemMapping,
    IntegrationProvider,
    IntegrationSyncRun,
    SyncRunStatus,
)
from app.modules.library.models import LibraryItem, LibraryItemStatus, MediaFile
from app.modules.metadata.models import (
    CreditType,
    Genre,
    MediaEpisode,
    MediaSeason,
    MediaWork,
    Person,
    WorkCredit,
    WorkGenre,
    WorkType,
)
from app.modules.personal.models import (
    CustomShelf,
    PersonalRecord,
    ShelfItem,
    WatchDiaryLog,
    WatchStatus,
)
from app.modules.playback.models import PlaybackProgress
from app.modules.sources.models import (
    DownloadTask,
    DownloadTaskStatus,
    ReleaseProvider,
    SourceRelease,
)


def test_metadata_work_with_genres_credits_and_episodes(db_session: Session) -> None:
    """Verify creating a MediaWork with genres, cast/crew credits, seasons, and episodes."""
    # 1. Create MediaWork
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=157336,
        imdb_id="tt0816692",
        title="Interstellar",
        original_title="Interstellar",
        persian_title="میان‌ستاره‌ای",
        original_language="en",
        overview="A team of explorers travel through a wormhole in space...",
        release_date=date(2014, 11, 7),
        release_year=2014,
        runtime_minutes=169,
        status="Released",
        tmdb_rating=8.4,
        tmdb_vote_count=35000,
        imdb_rating=8.7,
        imdb_votes=2000000,
        rotten_tomatoes_score=73,
        metascore=74,
    )
    db_session.add(work)
    db_session.flush()

    # 2. Genre and WorkGenre
    sci_fi = Genre(tmdb_genre_id=878, name="Science Fiction", persian_name="علمی تخیلی")
    db_session.add(sci_fi)
    db_session.flush()

    work_genre = WorkGenre(work_id=work.id, genre_id=sci_fi.id)
    db_session.add(work_genre)
    db_session.flush()

    # 3. People and Credits
    nolan = Person(
        tmdb_person_id=525,
        imdb_person_id="nm0634240",
        name="Christopher Nolan",
        known_for_department="Directing",
    )
    mcconaughey = Person(
        tmdb_person_id=10297,
        imdb_person_id="nm0000190",
        name="Matthew McConaughey",
        known_for_department="Acting",
    )
    db_session.add_all([nolan, mcconaughey])
    db_session.flush()

    dir_credit = WorkCredit(
        work_id=work.id,
        person_id=nolan.id,
        tmdb_credit_id="cr_dir_1",
        credit_type=CreditType.CREW,
        department="Directing",
        job="Director",
    )
    cast_credit = WorkCredit(
        work_id=work.id,
        person_id=mcconaughey.id,
        tmdb_credit_id="cr_cast_1",
        credit_type=CreditType.CAST,
        department="Acting",
        job="Actor",
        character_name="Cooper",
        billing_order=0,
    )
    db_session.add_all([dir_credit, cast_credit])
    db_session.commit()

    # 4. Query filmography by Person
    nolan_directed = db_session.scalars(
        select(MediaWork)
        .join(WorkCredit, WorkCredit.work_id == MediaWork.id)
        .where(
            WorkCredit.person_id == nolan.id,
            WorkCredit.credit_type == CreditType.CREW,
            WorkCredit.job == "Director",
        )
    ).all()
    assert len(nolan_directed) == 1
    assert nolan_directed[0].title == "Interstellar"
    assert nolan_directed[0].genres[0].name == "Science Fiction"


def test_library_and_media_file_relations(db_session: Session) -> None:
    """Verify LibraryItem and MediaFiles mapping to MediaWork."""
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=27205,
        imdb_id="tt1375666",
        title="Inception",
    )
    db_session.add(work)
    db_session.flush()

    library_item = LibraryItem(
        work_id=work.id,
        status=LibraryItemStatus.AVAILABLE,
        root_folder_path="/media/movies/Inception (2010)",
    )
    db_session.add(library_item)
    db_session.flush()

    media_file_1080p = MediaFile(
        library_item_id=library_item.id,
        file_path="/media/movies/Inception (2010)/Inception.2010.1080p.mkv",
        file_name="Inception.2010.1080p.mkv",
        file_size_bytes=2500000000,
        resolution="1080p",
        video_codec="x264",
        source_type="BluRay",
        audio_languages=["en"],
        has_soft_sub=True,
    )
    db_session.add(media_file_1080p)
    db_session.commit()

    loaded_work = db_session.get(MediaWork, work.id)
    assert loaded_work is not None
    assert loaded_work.library_item is not None
    assert loaded_work.library_item.status == LibraryItemStatus.AVAILABLE
    assert len(loaded_work.library_item.media_files) == 1
    assert loaded_work.library_item.media_files[0].resolution == "1080p"


def test_sources_and_download_tasks(db_session: Session) -> None:
    """Verify SourceRelease and DownloadTask relationship and progress tracking."""
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=603,
        imdb_id="tt0133093",
        title="The Matrix",
    )
    db_session.add(work)
    db_session.flush()

    item = LibraryItem(
        work_id=work.id,
        status=LibraryItemStatus.DOWNLOADING,
    )
    db_session.add(item)
    db_session.flush()

    release = SourceRelease(
        work_id=work.id,
        provider=ReleaseProvider.ZARFILM,
        download_url="https://dl.example.com/matrix.mkv",
        quality_label="1080p WEB-DL SoftSub",
        resolution="1080p",
        size_bytes=2200000000,
        has_persian_sub=True,
    )
    db_session.add(release)
    db_session.flush()

    task = DownloadTask(
        library_item_id=item.id,
        release_id=release.id,
        aria2_gid="aria2gid12345",
        download_url=release.download_url,
        destination_dir="/downloads/movies",
        file_name="matrix.mkv",
        status=DownloadTaskStatus.ACTIVE,
        total_bytes=2200000000,
        downloaded_bytes=1100000000,
        progress_percent=50.0,
        download_speed_bps=5000000,
    )
    db_session.add(task)
    db_session.commit()

    assert release.has_Persian_sub is True
    assert task.status == DownloadTaskStatus.ACTIVE
    assert task.progress_percent == 50.0


def test_playback_and_personal_tracking(db_session: Session) -> None:
    """Verify PlaybackProgress, PersonalRecord, WatchDiaryLog, and CustomShelf."""
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=238,
        imdb_id="tt0068646",
        title="The Godfather",
    )
    db_session.add(work)
    db_session.flush()

    # Playback
    progress = PlaybackProgress(
        work_id=work.id,
        position_seconds=3600,
        duration_seconds=10500,
        progress_percent=34.28,
        is_completed=False,
    )
    db_session.add(progress)

    # Personal record
    personal = PersonalRecord(
        work_id=work.id,
        watch_status=WatchStatus.COMPLETED,
        in_watchlist=False,
        is_favorite=True,
        user_rating=5.0,
        watch_count=2,
        personal_notes="Masterpiece",
        first_watched_at=date(2020, 1, 1),
        last_watched_at=date(2024, 5, 10),
    )
    db_session.add(personal)

    # Diary log
    log = WatchDiaryLog(
        work_id=work.id,
        watched_date=date(2024, 5, 10),
        rating_at_time=5.0,
        is_rewatch=True,
        review_text="Rewatched in 4K HDR",
        liked=True,
    )
    db_session.add(log)

    # Shelf and Item
    shelf = CustomShelf(
        name="Top Favorites",
        slug="top-favorites",
        description="All-time best cinema",
    )
    db_session.add(shelf)
    db_session.flush()

    shelf_item = ShelfItem(
        shelf_id=shelf.id,
        work_id=work.id,
        rank_order=1,
        note="Number 1 all time",
    )
    db_session.add(shelf_item)
    db_session.commit()

    loaded = db_session.get(MediaWork, work.id)
    assert loaded is not None
    assert loaded.personal_record is not None
    assert loaded.personal_record.is_favorite is True
    assert len(loaded.playback_progresses) == 1
    assert len(loaded.watch_diary_logs) == 1
    assert len(loaded.shelf_items) == 1
    assert loaded.shelf_items[0].shelf.name == "Top Favorites"


def test_integrations_and_uniqueness(db_session: Session) -> None:
    """Verify IntegrationSyncRun, ExternalItemMapping, and unique constraint enforcement."""
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=550,
        title="Fight Club",
    )
    db_session.add(work)
    db_session.flush()

    sync_run = IntegrationSyncRun(
        provider=IntegrationProvider.LETTERBOXD,
        sync_type="WATCHLIST",
        status=SyncRunStatus.SUCCESS,
        items_processed=100,
        items_created=5,
        items_updated=95,
    )
    db_session.add(sync_run)

    mapping = ExternalItemMapping(
        provider=IntegrationProvider.LETTERBOXD,
        external_key="letterboxd.com/film/fight-club/",
        work_id=work.id,
    )
    db_session.add(mapping)
    db_session.commit()

    # Attempt duplicate mapping with same provider and external_key
    dup_mapping = ExternalItemMapping(
        provider=IntegrationProvider.LETTERBOXD,
        external_key="letterboxd.com/film/fight-club/",
        work_id=work.id,
    )
    db_session.add(dup_mapping)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_delete_work(db_session: Session) -> None:
    """Verify deleting a MediaWork cascades to credits, seasons, library item, and personal record."""
    work = MediaWork(
        work_type=WorkType.SHOW,
        tmdb_id=1399,
        title="Game of Thrones",
    )
    db_session.add(work)
    db_session.flush()

    season = MediaSeason(
        work_id=work.id,
        season_number=1,
        title="Season 1",
    )
    db_session.add(season)
    db_session.flush()

    episode = MediaEpisode(
        work_id=work.id,
        season_id=season.id,
        season_number=1,
        episode_number=1,
        title="Winter Is Coming",
    )
    library_item = LibraryItem(work_id=work.id, status=LibraryItemStatus.WANTED)
    personal = PersonalRecord(work_id=work.id, watch_status=WatchStatus.WATCHING)

    db_session.add_all([episode, library_item, personal])
    db_session.commit()

    # Delete MediaWork
    db_session.delete(work)
    db_session.commit()

    assert db_session.get(MediaSeason, season.id) is None
    assert db_session.get(MediaEpisode, episode.id) is None
    assert db_session.get(LibraryItem, library_item.id) is None
    assert db_session.get(PersonalRecord, personal.id) is None
