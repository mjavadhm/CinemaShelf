"""Integration tests for frontend-facing endpoints (volumes, person details, downloads, CORS)."""

from collections.abc import Generator
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.aria2.client import Aria2GlobalStats, Aria2Port
from app.adapters.metadata_providers.client import (
    ExternalCredit,
    ExternalGenre,
    ExternalWorkDetails,
    MetadataProvidersPort,
)
from app.core.database import get_db_session
from app.main import app
from app.modules.downloads.router import get_sources_service as get_dl_sources_service
from app.modules.library.models import LibraryItem, LibraryItemStatus, MediaFile
from app.modules.library.router import get_library_service
from app.modules.library.service import LibraryService
from app.modules.metadata.models import CreditType, MediaWork, Person, WorkCredit, WorkType
from app.modules.metadata.router import get_metadata_service
from app.modules.metadata.service import MetadataService
from app.modules.sources.router import get_sources_service
from app.modules.sources.service import SourcesService


@pytest.fixture
def mock_aria2() -> MagicMock:
    client = MagicMock(spec=Aria2Port)
    client.get_global_stat.return_value = Aria2GlobalStats(
        download_speed_bps=5242880,
        upload_speed_bps=1048576,
        num_active=1,
        num_waiting=0,
        num_stopped=2,
    )
    return client


@pytest.fixture
def client(
    db_session: Session, mock_aria2: MagicMock
) -> Generator[TestClient, None, None]:
    meta_service = MetadataService(session=db_session)
    lib_service = LibraryService(session=db_session, metadata_service=meta_service)
    src_service = SourcesService(session=db_session, aria2_client=mock_aria2)

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_metadata_service] = lambda: meta_service
    app.dependency_overrides[get_library_service] = lambda: lib_service
    app.dependency_overrides[get_sources_service] = lambda: src_service
    app.dependency_overrides[get_dl_sources_service] = lambda: src_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_cors_headers(client: TestClient) -> None:
    """Ensure CORS middleware allows requests from frontend dev server."""
    resp = client.options(
        "/api/library/items",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_storage_volumes_endpoint(client: TestClient, db_session: Session) -> None:
    """Ensure storage volumes endpoint returns detected disk volumes with online status."""
    # Register a library item and media file with a simulated offline drive path
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=99901,
        title="Test Movie",
        release_year=2024,
    )
    db_session.add(work)
    db_session.flush()

    item = LibraryItem(
        work_id=work.id,
        status=LibraryItemStatus.AVAILABLE,
        root_folder_path="/run/media/user/Offline_Drive_1",
    )
    db_session.add(item)
    db_session.flush()

    media_file = MediaFile(
        library_item_id=item.id,
        file_path="/run/media/user/Offline_Drive_1/Movies/Test.mkv",
        file_name="Test.mkv",
        file_size_bytes=1024,
        resolution="1080p",
    )
    db_session.add(media_file)
    db_session.commit()

    resp = client.get("/api/library/volumes")
    assert resp.status_code == 200
    volumes = resp.json()
    assert len(volumes) >= 2  # At least downloads dir + offline drive

    # Find offline drive
    offline_vol = next((v for v in volumes if "Offline_Drive_1" in v["label"]), None)
    assert offline_vol is not None
    assert offline_vol["is_online"] is False

    # Also test non-prefixed endpoint
    resp2 = client.get("/library/volumes")
    assert resp2.status_code == 200


def test_person_details_and_filmography(client: TestClient, db_session: Session) -> None:
    """Ensure GET /metadata/people/{id} returns person details with cast and crew works."""
    person = Person(
        tmdb_person_id=456,
        name="Denis Villeneuve",
        original_name="Denis Villeneuve",
        persian_name="دنی ویلنوو",
        known_for_department="Directing",
    )
    db_session.add(person)
    db_session.flush()

    work1 = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=99902,
        title="Arrival",
        release_year=2016,
    )
    work2 = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=99903,
        title="Dune",
        release_year=2021,
    )
    db_session.add_all([work1, work2])
    db_session.flush()

    credit1 = WorkCredit(
        work_id=work1.id,
        person_id=person.id,
        credit_type=CreditType.CREW,
        department="Directing",
        job="Director",
    )
    credit2 = WorkCredit(
        work_id=work2.id,
        person_id=person.id,
        credit_type=CreditType.CAST,
        department="Acting",
        job="Actor",
        character_name="Cameo Guy",
    )
    db_session.add_all([credit1, credit2])
    db_session.commit()

    resp = client.get(f"/api/metadata/people/{person.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Denis Villeneuve"
    assert len(data["crew"]) == 1
    assert data["crew"][0]["work"]["title"] == "Arrival"
    assert len(data["cast"]) == 1
    assert data["cast"][0]["work"]["title"] == "Dune"
    assert data["cast"][0]["character_name"] == "Cameo Guy"

    # Test 404 for unknown person
    assert client.get("/api/metadata/people/999999").status_code == 404


def test_library_by_work_endpoint(client: TestClient, db_session: Session) -> None:
    """Ensure GET /api/library/by-work/{work_id} retrieves library item with files."""
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=99904,
        title="Inception",
        release_year=2010,
    )
    db_session.add(work)
    db_session.flush()

    item = LibraryItem(
        work_id=work.id,
        status=LibraryItemStatus.AVAILABLE,
    )
    db_session.add(item)
    db_session.flush()

    file1 = MediaFile(
        library_item_id=item.id,
        file_path="/tmp/fake_inception.mkv",
        file_name="fake_inception.mkv",
        resolution="2160p",
        video_codec="HEVC",
    )
    db_session.add(file1)
    db_session.commit()

    resp = client.get(f"/api/library/by-work/{work.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["work_id"] == work.id
    assert len(data["media_files"]) == 1
    assert data["media_files"][0]["resolution"] == "2160p"


def test_downloads_router(client: TestClient) -> None:
    """Ensure downloads router mounted at /downloads and /api/downloads works cleanly."""
    resp = client.get("/api/downloads/stats")
    assert resp.status_code == 200
    assert resp.json()["download_speed"] == 5242880

    list_resp = client.get("/api/downloads")
    assert list_resp.status_code == 200
    assert isinstance(list_resp.json(), list)
