"""Integration tests for Phase 3 Playback and Watch Status API endpoints."""

from collections.abc import Generator
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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
from app.modules.playback.router import get_playback_service
from app.modules.playback.service import PlaybackService


@pytest.fixture
def mock_metadata_provider() -> AsyncMock:
    provider = AsyncMock(spec=MetadataProvidersPort)
    provider.search.return_value = [
        ExternalSearchResult(
            tmdb_id=680,
            title="Pulp Fiction",
            work_type="MOVIE",
            release_year=1994,
            overview="The lives of two mob hitmen, a boxer...",
            vote_average=8.9,
        )
    ]
    provider.fetch_details.return_value = ExternalWorkDetails(
        tmdb_id=680,
        work_type="MOVIE",
        title="Pulp Fiction",
        imdb_id="tt0110912",
        original_title="Pulp Fiction",
        overview="The lives of two mob hitmen, a boxer...",
        release_date=date(1994, 10, 14),
        release_year=1994,
        runtime_minutes=154,
        status="Released",
        tmdb_rating=8.9,
        imdb_rating=8.9,
        genres=[ExternalGenre(tmdb_genre_id=80, name="Crime")],
        credits=[
            ExternalCredit(
                tmdb_person_id=138,
                name="Quentin Tarantino",
                credit_type="CREW",
                department="Directing",
                job="Director",
            )
        ],
    )
    return provider


@pytest.fixture
def mock_os_opener() -> MagicMock:
    opener = MagicMock()
    opener.open_file.return_value = True
    opener.open_folder.return_value = True
    return opener


@pytest.fixture
def client(
    db_session: Session,
    mock_metadata_provider: AsyncMock,
    mock_os_opener: MagicMock,
) -> Generator[TestClient, None, None]:
    meta_service = MetadataService(session=db_session, provider=mock_metadata_provider)
    lib_service = LibraryService(session=db_session, metadata_service=meta_service)
    play_service = PlaybackService(session=db_session, opener=mock_os_opener)

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_metadata_service] = lambda: meta_service
    app.dependency_overrides[get_library_service] = lambda: lib_service
    app.dependency_overrides[get_playback_service] = lambda: play_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_playback_and_watch_status_api_lifecycle(
    client: TestClient, tmp_path: Path, mock_os_opener: MagicMock
) -> None:
    # 1. Add movie to library
    add_resp = client.post(
        "/library/items",
        json={"tmdb_id": 680, "work_type": "MOVIE"},
    )
    assert add_resp.status_code == 201
    item_data = add_resp.json()
    item_id = item_data["id"]
    work_id = item_data["work"]["id"]

    # 2. Attach physical media file
    fake_video = tmp_path / "pulp_fiction.1080p.mkv"
    fake_video.write_bytes(b"dummy video data")

    file_resp = client.post(
        f"/library/items/{item_id}/files",
        json={
            "file_path": str(fake_video.resolve()),
            "file_name": "pulp_fiction.1080p.mkv",
            "resolution": "1080p",
        },
    )
    assert file_resp.status_code == 201
    media_file_id = file_resp.json()["id"]

    # 3. Open media file via API
    open_file_resp = client.post(f"/playback/files/{media_file_id}/open")
    assert open_file_resp.status_code == 200
    assert open_file_resp.json()["success"] is True
    assert open_file_resp.json()["action"] == "open_file"
    mock_os_opener.open_file.assert_called_with(str(fake_video.resolve()))

    # Invariant: Opening file does NOT mark as watched
    status_resp = client.get(f"/playback/works/{work_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["is_watched"] is False

    # 4. Open via work ID
    open_work_resp = client.post(f"/playback/works/{work_id}/open")
    assert open_work_resp.status_code == 200
    assert open_work_resp.json()["media_file_id"] == media_file_id

    # 5. Open file location in file manager
    loc_resp = client.post(f"/playback/files/{media_file_id}/open-location")
    assert loc_resp.status_code == 200
    assert loc_resp.json()["action"] == "open_location"
    assert loc_resp.json()["path"] == str(fake_video.parent.resolve())
    mock_os_opener.open_folder.assert_called_with(str(fake_video.parent.resolve()))

    # 6. Verify recently opened
    recent_resp = client.get("/playback/recently-opened")
    assert recent_resp.status_code == 200
    assert len(recent_resp.json()) == 1

    # 7. Manually mark as watched
    mark_resp = client.post(f"/playback/works/{work_id}/mark-watched")
    assert mark_resp.status_code == 200
    assert mark_resp.json()["is_watched"] is True

    # 8. Check watched list
    watched_resp = client.get("/playback/watched")
    assert watched_resp.status_code == 200
    assert len(watched_resp.json()) == 1
    assert watched_resp.json()[0]["work_id"] == work_id

    # 9. Manually mark as unwatched
    unmark_resp = client.post(f"/playback/works/{work_id}/mark-unwatched")
    assert unmark_resp.status_code == 200
    assert unmark_resp.json()["is_watched"] is False

    # Watched list is now empty
    watched_after = client.get("/playback/watched")
    assert len(watched_after.json()) == 0
