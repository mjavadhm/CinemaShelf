"""Unit tests for PlaybackService coordinating file opening and manual watch status."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ApplicationError, FileMissingError
from app.modules.library.models import LibraryItem, LibraryItemStatus, MediaFile
from app.modules.metadata.models import MediaWork, WorkType
from app.modules.playback.service import PlaybackService


@pytest.fixture
def mock_opener() -> MagicMock:
    opener = MagicMock()
    opener.open_file.return_value = True
    opener.open_folder.return_value = True
    return opener


@pytest.fixture
def sample_work(db_session: Session) -> MediaWork:
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=550,
        title="Fight Club",
        release_year=1999,
    )
    db_session.add(work)
    db_session.commit()
    return work


@pytest.fixture
def sample_library_item(db_session: Session, sample_work: MediaWork) -> LibraryItem:
    item = LibraryItem(
        work_id=sample_work.id,
        status=LibraryItemStatus.AVAILABLE,
    )
    db_session.add(item)
    db_session.commit()
    return item


@pytest.fixture
def sample_media_file(
    db_session: Session, sample_library_item: LibraryItem, tmp_path: Path
) -> MediaFile:
    real_file = tmp_path / "fight_club_1080p.mkv"
    real_file.write_bytes(b"sample video bytes")

    media_file = MediaFile(
        library_item_id=sample_library_item.id,
        file_path=str(real_file.resolve()),
        file_name="fight_club_1080p.mkv",
        file_size_bytes=1024,
        resolution="1080p",
    )
    db_session.add(media_file)
    db_session.commit()
    return media_file


def test_open_media_file_success(
    db_session: Session,
    sample_work: MediaWork,
    sample_media_file: MediaFile,
    mock_opener: MagicMock,
) -> None:
    service = PlaybackService(session=db_session, opener=mock_opener)

    resp = service.open_media_file(sample_media_file.id)
    assert resp.success is True
    assert resp.action == "open_file"
    assert resp.work_id == sample_work.id
    mock_opener.open_file.assert_called_once_with(sample_media_file.file_path)

    # Invariant verified: opening a file does NOT mark it as watched
    status = service.get_watch_status(sample_work.id)
    assert status.is_watched is False
    assert status.last_watched_at is not None


def test_open_media_file_missing_on_disk_raises(
    db_session: Session,
    sample_library_item: LibraryItem,
    mock_opener: MagicMock,
) -> None:
    media_file = MediaFile(
        library_item_id=sample_library_item.id,
        file_path="/tmp/non_existent_movie_path.mkv",
        file_name="non_existent_movie_path.mkv",
    )
    db_session.add(media_file)
    db_session.commit()

    service = PlaybackService(session=db_session, opener=mock_opener)
    with pytest.raises(FileMissingError, match="Media file not found on disk"):
        service.open_media_file(media_file.id)


def test_open_work_resolves_media_file(
    db_session: Session,
    sample_work: MediaWork,
    sample_media_file: MediaFile,
    mock_opener: MagicMock,
) -> None:
    service = PlaybackService(session=db_session, opener=mock_opener)

    resp = service.open_work(sample_work.id)
    assert resp.success is True
    assert resp.media_file_id == sample_media_file.id
    mock_opener.open_file.assert_called_once_with(sample_media_file.file_path)


def test_open_work_without_files_raises_404(
    db_session: Session,
    sample_work: MediaWork,
    mock_opener: MagicMock,
) -> None:
    # Library item exists but has no media files
    item = LibraryItem(work_id=sample_work.id, status=LibraryItemStatus.WANTED)
    db_session.add(item)
    db_session.commit()

    service = PlaybackService(session=db_session, opener=mock_opener)
    with pytest.raises(ApplicationError) as exc_info:
        service.open_work(sample_work.id)
    assert exc_info.value.code == "no_media_files_available"


def test_open_file_location_success(
    db_session: Session,
    sample_media_file: MediaFile,
    mock_opener: MagicMock,
) -> None:
    service = PlaybackService(session=db_session, opener=mock_opener)

    resp = service.open_file_location(sample_media_file.id)
    assert resp.success is True
    assert resp.action == "open_location"
    parent_dir = str(Path(sample_media_file.file_path).parent)
    assert resp.path == parent_dir
    mock_opener.open_folder.assert_called_once_with(parent_dir)


def test_manual_mark_watched_and_unwatched(
    db_session: Session,
    sample_work: MediaWork,
    mock_opener: MagicMock,
) -> None:
    service = PlaybackService(session=db_session, opener=mock_opener)

    # Initial status
    initial = service.get_watch_status(sample_work.id)
    assert initial.is_watched is False

    # Mark as watched
    watched = service.mark_watched(sample_work.id)
    assert watched.is_completed is True

    status = service.get_watch_status(sample_work.id)
    assert status.is_watched is True
    assert status.last_watched_at is not None

    # Verify listing in watched
    watched_list = service.list_watched()
    assert len(watched_list) == 1
    assert watched_list[0].work_id == sample_work.id

    # Mark as unwatched
    unwatched = service.mark_unwatched(sample_work.id)
    assert unwatched.is_completed is False

    status_after = service.get_watch_status(sample_work.id)
    assert status_after.is_watched is False
    assert len(service.list_watched()) == 0
