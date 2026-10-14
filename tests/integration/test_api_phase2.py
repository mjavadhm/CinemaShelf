"""Integration tests for Phase 2 Sources and Download API endpoints."""

from collections.abc import Generator
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.aria2.client import Aria2GlobalStats
from app.adapters.metadata_providers.client import (
    ExternalCredit,
    ExternalGenre,
    ExternalSearchResult,
    ExternalWorkDetails,
    MetadataProvidersPort,
)
from app.adapters.zarfilm.client import ZarfilmReleaseCandidate
from app.core.database import get_db_session
from app.main import app
from app.modules.library.router import get_library_service
from app.modules.library.service import LibraryService
from app.modules.metadata.router import get_metadata_service
from app.modules.metadata.service import MetadataService
from app.modules.sources.router import get_sources_service
from app.modules.sources.service import SourcesService


@pytest.fixture
def mock_metadata_provider() -> AsyncMock:
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
def mock_aria2() -> MagicMock:
    client = MagicMock()
    client.add_uri.return_value = "aria2_gid_999"
    client.pause.return_value = True
    client.unpause.return_value = True
    client.remove.return_value = True
    client.get_global_stat.return_value = Aria2GlobalStats(
        download_speed_bps=5242880,
        upload_speed_bps=10240,
        num_active=2,
        num_waiting=1,
        num_stopped=3,
    )
    client.change_global_option.return_value = True
    return client


@pytest.fixture
def mock_zarfilm() -> MagicMock:
    client = MagicMock()
    client.search_and_extract.return_value = (
        "https://zarfilm.com/movies/interstellar-2014/",
        [
            ZarfilmReleaseCandidate(
                download_url="https://dl.zarfilm.com/interstellar_1080p_softsub.mkv",
                quality_label="1080p WEB-DL x265 SoftSub (PSA)",
                resolution="1080p",
                encoder="PSA",
                size_text="2.4 GB",
                size_bytes=2576980377,
                is_dubbed=False,
                has_persian_sub=True,
                is_x265=True,
            )
        ],
    )
    return client


@pytest.fixture
def client(
    db_session: Session,
    mock_metadata_provider: AsyncMock,
    mock_aria2: MagicMock,
    mock_zarfilm: MagicMock,
) -> Generator[TestClient, None, None]:
    meta_service = MetadataService(session=db_session, provider=mock_metadata_provider)
    lib_service = LibraryService(session=db_session, metadata_service=meta_service)
    src_service = SourcesService(
        session=db_session,
        aria2_client=mock_aria2,
        zarfilm_client=mock_zarfilm,
    )

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_metadata_service] = lambda: meta_service
    app.dependency_overrides[get_library_service] = lambda: lib_service
    app.dependency_overrides[get_sources_service] = lambda: src_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_discover_releases_flow(client: TestClient) -> None:
    # 1. Add movie to library
    add_resp = client.post(
        "/library/items",
        json={"tmdb_id": 157336, "work_type": "MOVIE"},
    )
    assert add_resp.status_code == 201
    item_data = add_resp.json()
    work_id = item_data["work"]["id"]

    # 2. Discover releases via Zarfilm scraper endpoint
    disc_resp = client.post(f"/sources/works/{work_id}/discover")
    assert disc_resp.status_code == 200
    disc_data = disc_resp.json()
    assert disc_data["work_id"] == work_id
    assert disc_data["total_found"] == 1
    assert len(disc_data["releases"]) == 1

    rel = disc_data["releases"][0]
    assert rel["quality_label"] == "1080p WEB-DL x265 SoftSub (PSA)"
    assert rel["resolution"] == "1080p"
    assert rel["has_persian_sub"] is True

    # 3. Retrieve saved releases
    list_resp = client.get(f"/sources/works/{work_id}/releases")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_download_task_crud_and_controls(client: TestClient) -> None:
    # 1. Add movie
    add_resp = client.post(
        "/library/items",
        json={"tmdb_id": 157336, "work_type": "MOVIE"},
    )
    item_data = add_resp.json()
    item_id = item_data["id"]
    work_id = item_data["work"]["id"]

    # 2. Discover releases
    disc_resp = client.post(f"/sources/works/{work_id}/discover")
    release_id = disc_resp.json()["releases"][0]["id"]

    # 3. Start download task
    task_resp = client.post(
        "/sources/downloads",
        json={"library_item_id": item_id, "release_id": release_id},
    )
    assert task_resp.status_code == 201
    task_data = task_resp.json()
    task_id = task_data["id"]
    assert task_data["status"] == "ACTIVE"
    assert task_data["aria2_gid"] == "aria2_gid_999"

    # 4. Get task by ID
    get_resp = client.get(f"/sources/downloads/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == task_id

    # 5. List downloads
    list_resp = client.get("/sources/downloads?status=ACTIVE")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 6. Pause task
    pause_resp = client.post(f"/sources/downloads/{task_id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "PAUSED"

    # 7. Resume task
    resume_resp = client.post(f"/sources/downloads/{task_id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "ACTIVE"

    # 8. Cancel task
    cancel_resp = client.delete(f"/sources/downloads/{task_id}")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "REMOVED"


def test_aria2_stats_and_speed_limit(client: TestClient) -> None:
    stats_resp = client.get("/sources/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["download_speed"] == 5242880
    assert stats["num_active"] == 2

    limit_resp = client.post(
        "/sources/speed-limit",
        json={"max_download_limit_kb": 2048},
    )
    assert limit_resp.status_code == 204
