"""Unit tests for background download synchronization and JIT queueing handlers."""

from pathlib import Path
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.adapters.aria2.client import Aria2TaskStatus
from app.jobs.handlers import (
    is_within_schedule,
    process_queued_downloads_jit,
    sync_active_downloads,
)
from app.modules.library.models import LibraryItem, LibraryItemStatus
from app.modules.metadata.models import MediaWork, WorkType
from app.modules.sources.models import DownloadTask, DownloadTaskStatus
from app.modules.sources.service import SourcesService


def test_is_within_schedule() -> None:
    # Standard daytime or morning window: 2 to 7
    assert is_within_schedule(2, 7, current_hour=2) is True
    assert is_within_schedule(2, 7, current_hour=4) is True
    assert is_within_schedule(2, 7, current_hour=1) is False
    assert is_within_schedule(2, 7, current_hour=7) is False

    # Overnight wraparound window: 22 to 6
    assert is_within_schedule(22, 6, current_hour=23) is True
    assert is_within_schedule(22, 6, current_hour=2) is True
    assert is_within_schedule(22, 6, current_hour=21) is False
    assert is_within_schedule(22, 6, current_hour=6) is False


def test_sync_active_downloads_completes_and_attaches_media_file(
    db_session: Session, tmp_path: Path
) -> None:
    work = MediaWork(work_type=WorkType.MOVIE, tmdb_id=999, title="Test Film")
    db_session.add(work)
    db_session.flush()

    item = LibraryItem(work_id=work.id, status=LibraryItemStatus.DOWNLOADING)
    db_session.add(item)
    db_session.flush()

    fake_file = tmp_path / "test_film.1080p.mkv"
    fake_file.write_bytes(b"dummy video data of some length")

    task = DownloadTask(
        library_item_id=item.id,
        aria2_gid="complete_gid",
        download_url="https://example.com/film.mkv",
        destination_dir=str(tmp_path),
        file_name="test_film.1080p.mkv",
        status=DownloadTaskStatus.ACTIVE,
    )
    db_session.add(task)
    db_session.commit()

    mock_aria2 = MagicMock()
    mock_aria2.tell_status.return_value = Aria2TaskStatus(
        gid="complete_gid",
        status="complete",
        total_length_bytes=1000,
        completed_length_bytes=1000,
        download_speed_bps=0,
        files=[{"path": str(fake_file)}],
    )

    completed = sync_active_downloads(db_session, mock_aria2)
    assert completed == 1

    # Verify task state
    db_session.refresh(task)
    assert task.status == DownloadTaskStatus.COMPLETED
    assert task.progress_percent == 100.0
    assert task.completed_at is not None

    # Verify LibraryItem updated to AVAILABLE and MediaFile registered
    db_session.refresh(item)
    assert item.status == LibraryItemStatus.AVAILABLE

    assert len(item.media_files) == 1
    assert item.media_files[0].file_name == "test_film.1080p.mkv"
    assert item.media_files[0].resolution == "1080p"


def test_sync_active_downloads_handles_error(db_session: Session) -> None:
    work = MediaWork(work_type=WorkType.MOVIE, tmdb_id=888, title="Failed Film")
    db_session.add(work)
    db_session.flush()

    item = LibraryItem(work_id=work.id, status=LibraryItemStatus.DOWNLOADING)
    db_session.add(item)
    db_session.flush()

    task = DownloadTask(
        library_item_id=item.id,
        aria2_gid="error_gid",
        download_url="https://example.com/failed.mkv",
        destination_dir="/tmp",
        status=DownloadTaskStatus.ACTIVE,
    )
    db_session.add(task)
    db_session.commit()

    mock_aria2 = MagicMock()
    mock_aria2.tell_status.return_value = Aria2TaskStatus(
        gid="error_gid",
        status="error",
        error_message="HTTP 404 Not Found",
    )

    completed = sync_active_downloads(db_session, mock_aria2)
    assert completed == 0

    db_session.refresh(task)
    assert task.status == DownloadTaskStatus.ERROR
    assert task.error_message == "HTTP 404 Not Found"


def test_process_queued_downloads_jit(db_session: Session) -> None:
    work = MediaWork(work_type=WorkType.MOVIE, tmdb_id=777, title="Queued Film")
    db_session.add(work)
    db_session.flush()

    item = LibraryItem(work_id=work.id, status=LibraryItemStatus.WANTED)
    db_session.add(item)
    db_session.flush()

    task = DownloadTask(
        library_item_id=item.id,
        download_url="https://example.com/queued.mkv",
        destination_dir="/tmp",
        status=DownloadTaskStatus.QUEUED,
    )
    db_session.add(task)
    db_session.commit()

    mock_aria2 = MagicMock()
    mock_aria2.add_uri.return_value = "new_gid_456"

    service = SourcesService(session=db_session, aria2_client=mock_aria2)

    # With max_concurrent=2 and 0 active downloads, 1 queued task should activate
    activated = process_queued_downloads_jit(
        db_session, sources_service=service, max_concurrent=2
    )
    assert activated == 1

    db_session.refresh(task)
    assert task.status == DownloadTaskStatus.ACTIVE
    assert task.aria2_gid == "new_gid_456"
