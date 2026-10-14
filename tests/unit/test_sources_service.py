"""Unit tests for SourcesService coordinating releases and download tasks."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.adapters.aria2.client import Aria2GlobalStats
from app.adapters.zarfilm.client import ZarfilmReleaseCandidate
from app.core.errors import ApplicationError
from app.modules.library.models import LibraryItem, LibraryItemStatus
from app.modules.metadata.models import MediaWork, WorkType
from app.modules.sources.models import (
    DownloadTaskStatus,
    ReleaseProvider,
    SourceRelease,
)
from app.modules.sources.schemas import DownloadTaskCreate
from app.modules.sources.service import SourcesService


@pytest.fixture
def sample_work(db_session: Session) -> MediaWork:
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=12345,
        title="Interstellar",
        release_year=2014,
    )
    db_session.add(work)
    db_session.commit()
    return work


@pytest.fixture
def sample_library_item(db_session: Session, sample_work: MediaWork) -> LibraryItem:
    item = LibraryItem(
        work_id=sample_work.id,
        status=LibraryItemStatus.WANTED,
    )
    db_session.add(item)
    db_session.commit()
    return item


@pytest.fixture
def mock_aria2() -> MagicMock:
    client = MagicMock()
    client.add_uri.return_value = "mock_gid_123"
    client.pause.return_value = True
    client.unpause.return_value = True
    client.remove.return_value = True
    client.get_global_stat.return_value = Aria2GlobalStats(
        download_speed_bps=204800,
        upload_speed_bps=0,
        num_active=1,
        num_waiting=0,
        num_stopped=0,
    )
    return client


@pytest.fixture
def mock_zarfilm() -> MagicMock:
    client = MagicMock()
    client.search_and_extract.return_value = (
        "https://zarfilm.com/movies/interstellar-2014/",
        [
            ZarfilmReleaseCandidate(
                download_url="https://dl.zarfilm.com/interstellar_1080p.mkv",
                quality_label="1080p WEB-DL SoftSub",
                resolution="1080p",
                encoder="PSA",
                size_text="2.5 GB",
                size_bytes=2684354560,
                has_persian_sub=True,
                is_dubbed=False,
                is_x265=True,
            )
        ],
    )
    return client


def test_discover_and_save_releases(
    db_session: Session,
    sample_work: MediaWork,
    mock_aria2: MagicMock,
    mock_zarfilm: MagicMock,
) -> None:
    service = SourcesService(
        session=db_session,
        aria2_client=mock_aria2,
        zarfilm_client=mock_zarfilm,
    )

    page_url, releases = service.discover_and_save_releases(sample_work.id)
    assert page_url == "https://zarfilm.com/movies/interstellar-2014/"
    assert len(releases) == 1
    assert releases[0].work_id == sample_work.id
    assert releases[0].download_url == "https://dl.zarfilm.com/interstellar_1080p.mkv"
    assert releases[0].provider == ReleaseProvider.ZARFILM
    assert releases[0].has_persian_sub is True


def test_discover_releases_work_not_found(
    db_session: Session,
    mock_aria2: MagicMock,
    mock_zarfilm: MagicMock,
) -> None:
    service = SourcesService(
        session=db_session,
        aria2_client=mock_aria2,
        zarfilm_client=mock_zarfilm,
    )
    with pytest.raises(ApplicationError) as exc_info:
        service.discover_and_save_releases(99999)
    assert exc_info.value.code == "work_not_found"


def test_create_download_task_with_release(
    db_session: Session,
    sample_work: MediaWork,
    sample_library_item: LibraryItem,
    mock_aria2: MagicMock,
    mock_zarfilm: MagicMock,
) -> None:
    service = SourcesService(
        session=db_session,
        aria2_client=mock_aria2,
        zarfilm_client=mock_zarfilm,
    )
    release = SourceRelease(
        work_id=sample_work.id,
        provider=ReleaseProvider.ZARFILM,
        download_url="https://dl.zarfilm.com/interstellar_1080p.mkv",
        quality_label="1080p",
    )
    db_session.add(release)
    db_session.commit()

    task = service.create_download_task(
        DownloadTaskCreate(
            library_item_id=sample_library_item.id,
            release_id=release.id,
        ),
        start_immediately=True,
    )

    assert task.status == DownloadTaskStatus.ACTIVE
    assert task.aria2_gid == "mock_gid_123"
    assert task.download_url == release.download_url
    assert sample_library_item.status == LibraryItemStatus.DOWNLOADING
    mock_aria2.add_uri.assert_called_once()


def test_create_download_task_queued(
    db_session: Session,
    sample_library_item: LibraryItem,
    mock_aria2: MagicMock,
    mock_zarfilm: MagicMock,
) -> None:
    service = SourcesService(
        session=db_session,
        aria2_client=mock_aria2,
        zarfilm_client=mock_zarfilm,
    )

    task = service.create_download_task(
        DownloadTaskCreate(
            library_item_id=sample_library_item.id,
            download_url="https://example.com/direct.mkv",
        ),
        start_immediately=False,
    )

    assert task.status == DownloadTaskStatus.QUEUED
    assert task.aria2_gid is None
    mock_aria2.add_uri.assert_not_called()


def test_pause_resume_cancel_download_task(
    db_session: Session,
    sample_library_item: LibraryItem,
    mock_aria2: MagicMock,
    mock_zarfilm: MagicMock,
) -> None:
    service = SourcesService(
        session=db_session,
        aria2_client=mock_aria2,
        zarfilm_client=mock_zarfilm,
    )

    task = service.create_download_task(
        DownloadTaskCreate(
            library_item_id=sample_library_item.id,
            download_url="https://example.com/direct.mkv",
        ),
        start_immediately=True,
    )
    assert task.status == DownloadTaskStatus.ACTIVE

    # Pause
    paused = service.pause_download(task.id)
    assert paused.status == DownloadTaskStatus.PAUSED
    mock_aria2.pause.assert_called_with("mock_gid_123")

    # Resume
    resumed = service.resume_download(task.id)
    assert resumed.status == DownloadTaskStatus.ACTIVE
    mock_aria2.unpause.assert_called_with("mock_gid_123")

    # Cancel
    cancelled = service.cancel_download(task.id)
    assert cancelled.status == DownloadTaskStatus.REMOVED
    mock_aria2.remove.assert_called_with("mock_gid_123")


def test_get_aria2_stats_and_speed_limit(
    db_session: Session,
    mock_aria2: MagicMock,
    mock_zarfilm: MagicMock,
) -> None:
    service = SourcesService(
        session=db_session,
        aria2_client=mock_aria2,
        zarfilm_client=mock_zarfilm,
    )

    stats = service.get_aria2_stats()
    assert stats.download_speed == 204800
    assert stats.num_active == 1

    service.set_speed_limit(500)
    mock_aria2.change_global_option.assert_called_with(
        {"max-overall-download-limit": "512000"}
    )
