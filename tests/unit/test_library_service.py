"""Unit tests for LibraryService."""

from datetime import date
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.orm import Session

from app.adapters.metadata_providers.client import (
    ExternalGenre,
    ExternalWorkDetails,
    MetadataProvidersPort,
)
from app.core.errors import ApplicationError
from app.modules.library.models import LibraryItemStatus
from app.modules.library.schemas import LibraryItemCreate, MediaFileCreate
from app.modules.library.service import LibraryService
from app.modules.metadata.models import MediaWork, WorkType
from app.modules.metadata.service import MetadataService


@pytest.fixture
def test_work(db_session: Session) -> MediaWork:
    """Fixture creating a test MediaWork in the database."""
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=603,
        imdb_id="tt0133093",
        title="The Matrix",
        release_year=1999,
    )
    db_session.add(work)
    db_session.commit()
    return work


@pytest.mark.asyncio
async def test_add_to_library_via_work_id(
    db_session: Session, test_work: MediaWork
) -> None:
    """Verify adding an existing MediaWork to the library as WANTED."""
    service = LibraryService(session=db_session)
    req = LibraryItemCreate(
        work_id=test_work.id,
        status=LibraryItemStatus.WANTED,
        root_folder_path="/media/movies/The Matrix (1999)",
    )

    item = await service.add_to_library(req)
    assert item.id is not None
    assert item.work_id == test_work.id
    assert item.status == LibraryItemStatus.WANTED
    assert item.root_folder_path == "/media/movies/The Matrix (1999)"


@pytest.mark.asyncio
async def test_add_to_library_via_tmdb_id_auto_ingests(db_session: Session) -> None:
    """Verify specifying tmdb_id fetches metadata and adds the item in one step."""
    mock_provider = AsyncMock(spec=MetadataProvidersPort)
    mock_provider.fetch_details.return_value = ExternalWorkDetails(
        tmdb_id=27205,
        work_type="MOVIE",
        title="Inception",
        release_date=date(2010, 7, 16),
        release_year=2010,
        genres=[ExternalGenre(tmdb_genre_id=28, name="Action")],
        credits=[],
    )
    meta_service = MetadataService(session=db_session, provider=mock_provider)
    lib_service = LibraryService(session=db_session, metadata_service=meta_service)

    req = LibraryItemCreate(
        tmdb_id=27205,
        work_type=WorkType.MOVIE,
        status=LibraryItemStatus.WANTED,
    )

    item = await lib_service.add_to_library(req)
    assert item.id is not None
    assert item.work.title == "Inception"
    assert item.status == LibraryItemStatus.WANTED


@pytest.mark.asyncio
async def test_add_duplicate_to_library_raises_conflict(
    db_session: Session, test_work: MediaWork
) -> None:
    """Verify attempting to add the same work twice raises a 409 conflict error."""
    service = LibraryService(session=db_session)
    req = LibraryItemCreate(work_id=test_work.id, status=LibraryItemStatus.WANTED)

    await service.add_to_library(req)

    with pytest.raises(ApplicationError) as exc_info:
        await service.add_to_library(req)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "item_already_in_library"


@pytest.mark.asyncio
async def test_attach_media_file_promotes_status_to_available(
    db_session: Session, test_work: MediaWork
) -> None:
    """Verify registering a physical file transitions WANTED item to AVAILABLE."""
    service = LibraryService(session=db_session)
    req = LibraryItemCreate(work_id=test_work.id, status=LibraryItemStatus.WANTED)
    item = await service.add_to_library(req)

    file_req = MediaFileCreate(
        file_path="/media/movies/The Matrix (1999)/matrix.1080p.mkv",
        file_name="matrix.1080p.mkv",
        file_size_bytes=2200000000,
        resolution="1080p",
        video_codec="x265",
        source_type="BluRay",
        audio_languages=["en"],
        has_soft_sub=True,
    )
    media_file = service.attach_media_file(item.id, file_req)

    assert media_file.id is not None
    assert media_file.resolution == "1080p"

    # Reload item to verify status transition
    reloaded_item = service.get_item(item.id)
    assert reloaded_item.status == LibraryItemStatus.AVAILABLE
    assert len(reloaded_item.media_files) == 1


@pytest.mark.asyncio
async def test_attach_duplicate_file_path_raises_conflict(
    db_session: Session, test_work: MediaWork
) -> None:
    """Verify attaching an already existing file path raises conflict error."""
    service = LibraryService(session=db_session)
    req = LibraryItemCreate(work_id=test_work.id, status=LibraryItemStatus.WANTED)
    item = await service.add_to_library(req)

    file_req = MediaFileCreate(
        file_path="/media/movies/The Matrix (1999)/matrix.mkv",
        file_name="matrix.mkv",
    )
    service.attach_media_file(item.id, file_req)

    with pytest.raises(ApplicationError) as exc_info:
        service.attach_media_file(item.id, file_req)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "duplicate_file_path"


@pytest.mark.asyncio
async def test_rematch_item_transfers_files(
    db_session: Session, test_work: MediaWork
) -> None:
    """Verify rematching an item updates work and transfers physical files cleanly."""
    mock_provider = AsyncMock(spec=MetadataProvidersPort)
    mock_provider.fetch_details.return_value = ExternalWorkDetails(
        tmdb_id=27205,
        work_type="MOVIE",
        title="Inception",
        release_date=date(2010, 7, 16),
        release_year=2010,
        genres=[],
        credits=[],
    )
    meta_service = MetadataService(session=db_session, provider=mock_provider)
    service = LibraryService(session=db_session, metadata_service=meta_service)

    # Add initial work (The Matrix)
    req = LibraryItemCreate(work_id=test_work.id, status=LibraryItemStatus.WANTED)
    item = await service.add_to_library(req)

    # Attach file
    file_req = MediaFileCreate(
        file_path="/media/movies/Inception.2010.mkv",
        file_name="Inception.2010.mkv",
        resolution="1080p",
    )
    service.attach_media_file(item.id, file_req)

    # Rematch to Inception
    rematched = await service.rematch_item(item.id, target_tmdb_id=27205)
    assert rematched.work.title == "Inception"
    assert rematched.work.release_year == 2010
    assert len(rematched.media_files) == 1
    assert rematched.media_files[0].file_name == "Inception.2010.mkv"
