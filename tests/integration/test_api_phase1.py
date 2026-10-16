"""Integration tests for Phase 1 FastAPI endpoints."""

from collections.abc import Generator
from datetime import date
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.metadata_providers.client import (
    ExternalCredit,
    ExternalGenre,
    ExternalSearchResult,
    ExternalWorkDetails,
    MetadataProvidersPort,
)
from app.core.database import get_db_session
from app.main import app
from app.modules.library.router import get_library_service
from app.modules.library.service import LibraryService
from app.modules.metadata.router import get_metadata_service
from app.modules.metadata.service import MetadataService


@pytest.fixture
def mock_provider() -> AsyncMock:
    """Mock metadata provider returning realistic movie payloads."""
    provider = AsyncMock(spec=MetadataProvidersPort)
    provider.search.return_value = [
        ExternalSearchResult(
            tmdb_id=157336,
            title="Interstellar",
            work_type="MOVIE",
            release_year=2014,
            overview="A team of explorers travel through a wormhole...",
            vote_average=8.4,
        )
    ]
    provider.fetch_details.return_value = ExternalWorkDetails(
        tmdb_id=157336,
        work_type="MOVIE",
        title="Interstellar",
        imdb_id="tt0816692",
        original_title="Interstellar",
        overview="A team of explorers travel through a wormhole...",
        release_date=date(2014, 11, 7),
        release_year=2014,
        runtime_minutes=169,
        status="Released",
        tmdb_rating=8.4,
        imdb_rating=8.7,
        genres=[ExternalGenre(tmdb_genre_id=878, name="Science Fiction")],
        credits=[
            ExternalCredit(
                tmdb_person_id=525,
                name="Christopher Nolan",
                credit_type="CREW",
                department="Directing",
                job="Director",
            )
        ],
    )
    return provider


@pytest.fixture
def client(
    db_session: Session, mock_provider: AsyncMock
) -> Generator[TestClient, None, None]:
    """Provide a TestClient with dependency overrides bound to isolated test database."""
    meta_service = MetadataService(session=db_session, provider=mock_provider)
    lib_service = LibraryService(session=db_session, metadata_service=meta_service)

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_metadata_service] = lambda: meta_service
    app.dependency_overrides[get_library_service] = lambda: lib_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_metadata_search_endpoint(client: TestClient) -> None:
    """Verify GET /metadata/search endpoint."""
    response = client.get("/metadata/search?query=Interstellar&year=2014")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tmdb_id"] == 157336
    assert data[0]["title"] == "Interstellar"


def test_metadata_ingest_and_catalog_flow(client: TestClient) -> None:
    """Verify POST /metadata/ingest and subsequent retrieval via GET /metadata/works."""
    ingest_resp = client.post(
        "/metadata/ingest",
        json={"tmdb_id": 157336, "work_type": "MOVIE"},
    )
    assert ingest_resp.status_code == 201
    work_data = ingest_resp.json()
    work_id = work_data["id"]
    assert work_data["title"] == "Interstellar"
    assert len(work_data["genres"]) == 1
    assert len(work_data["credits"]) == 1

    # Verify listing
    list_resp = client.get("/metadata/works")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(w["id"] == work_id for w in items)

    # Verify detail
    detail_resp = client.get(f"/metadata/works/{work_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == work_id


def test_full_library_crud_lifecycle(client: TestClient) -> None:
    """Verify adding item to library via tmdb_id, updating status, attaching files, and deletion."""
    # 1. Add to library (auto-ingesting metadata)
    add_resp = client.post(
        "/library/items",
        json={
            "tmdb_id": 157336,
            "work_type": "MOVIE",
            "status": "WANTED",
            "root_folder_path": "/media/movies/Interstellar (2014)",
        },
    )
    assert add_resp.status_code == 201
    item = add_resp.json()
    item_id = item["id"]
    assert item["status"] == "WANTED"
    assert item["work"]["title"] == "Interstellar"

    # 2. List library items
    list_resp = client.get("/library/items?status=WANTED")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 3. Patch status to DOWNLOADING
    patch_resp = client.patch(
        f"/library/items/{item_id}/status",
        json={"status": "DOWNLOADING"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "DOWNLOADING"

    # 4. Attach physical media file (should promote to AVAILABLE)
    file_resp = client.post(
        f"/library/items/{item_id}/files",
        json={
            "file_path": "/media/movies/Interstellar (2014)/Interstellar.2014.1080p.mkv",
            "file_name": "Interstellar.2014.1080p.mkv",
            "file_size_bytes": 3500000000,
            "resolution": "1080p",
            "video_codec": "x265",
            "has_soft_sub": True,
        },
    )
    assert file_resp.status_code == 201
    assert file_resp.json()["resolution"] == "1080p"

    # Verify item status transitioned to AVAILABLE
    get_resp = client.get(f"/library/items/{item_id}")
    assert get_resp.status_code == 200
    item_detail = get_resp.json()
    assert item_detail["status"] == "AVAILABLE"
    assert len(item_detail["media_files"]) == 1

    # 5. Delete item from library
    del_resp = client.delete(f"/library/items/{item_id}")
    assert del_resp.status_code == 204

    # Confirm 404
    assert client.get(f"/library/items/{item_id}").status_code == 404


def test_rematch_library_item_endpoint(client: TestClient, mock_provider: AsyncMock) -> None:
    """Verify rematching a library item re-identifies work and transfers files."""
    # Mocking target details for another film
    mock_provider.fetch_details.return_value = ExternalWorkDetails(
        tmdb_id=27205,
        work_type="MOVIE",
        title="Inception",
        release_date=date(2010, 7, 16),
        release_year=2010,
        genres=[],
        credits=[],
    )

    # Ingest original work (157336) and add to library
    ingest_resp = client.post("/metadata/ingest", json={"tmdb_id": 157336, "work_type": "MOVIE"})
    work_id = ingest_resp.json()["id"]

    lib_resp = client.post("/library/items", json={"work_id": work_id, "status": "WANTED"})
    item_id = lib_resp.json()["id"]

    # Attach file
    client.post(
        f"/library/items/{item_id}/files",
        json={
            "file_path": "/media/movies/movie.mkv",
            "file_name": "movie.mkv",
            "resolution": "1080p",
        },
    )

    # Call rematch endpoint
    rematch_resp = client.post(
        f"/library/items/{item_id}/rematch",
        json={"tmdb_id": 27205, "work_type": "MOVIE"},
    )
    assert rematch_resp.status_code == 200
    rematch_data = rematch_resp.json()
    assert rematch_data["work"]["title"] == "Inception"
    assert rematch_data["work"]["release_year"] == 2010
    assert len(rematch_data["media_files"]) == 1
    assert rematch_data["media_files"][0]["file_name"] == "movie.mkv"

    # Also test by-work rematch endpoint
    by_work_resp = client.post(
        f"/library/by-work/{rematch_data['work_id']}/rematch",
        json={"tmdb_id": 27205, "work_type": "MOVIE"},
    )
    assert by_work_resp.status_code == 200
    assert by_work_resp.json()["work"]["title"] == "Inception"
