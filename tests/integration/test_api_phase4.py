"""Integration tests for Phase 4 Personalization, Ratings, Diary, and Custom Shelves."""

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
from app.modules.personal.router import get_personal_service
from app.modules.personal.service import PersonalService


@pytest.fixture
def mock_metadata_provider() -> AsyncMock:
    provider = AsyncMock(spec=MetadataProvidersPort)
    provider.search.return_value = [
        ExternalSearchResult(
            tmdb_id=680,
            title="Pulp Fiction",
            work_type="MOVIE",
            release_year=1994,
            overview="Two mob hitmen, a boxer...",
            vote_average=8.9,
        )
    ]
    provider.fetch_details.return_value = ExternalWorkDetails(
        tmdb_id=680,
        work_type="MOVIE",
        title="Pulp Fiction",
        imdb_id="tt0110912",
        original_title="Pulp Fiction",
        overview="Two mob hitmen, a boxer...",
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
def client(
    db_session: Session,
    mock_metadata_provider: AsyncMock,
) -> Generator[TestClient, None, None]:
    meta_service = MetadataService(session=db_session, provider=mock_metadata_provider)
    lib_service = LibraryService(session=db_session, metadata_service=meta_service)
    personal_service = PersonalService(session=db_session)

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_metadata_service] = lambda: meta_service
    app.dependency_overrides[get_library_service] = lambda: lib_service
    app.dependency_overrides[get_personal_service] = lambda: personal_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_personal_records_api_lifecycle(client: TestClient) -> None:
    # 1. Add movie to library
    add_resp = client.post(
        "/library/items",
        json={"tmdb_id": 680, "work_type": "MOVIE"},
    )
    assert add_resp.status_code == 201
    work_id = add_resp.json()["work"]["id"]

    # 2. Get initial personal record
    rec_resp = client.get(f"/personal/records/{work_id}")
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    assert rec_data["watch_status"] == "UNWATCHED"
    assert rec_data["in_watchlist"] is False
    assert rec_data["user_rating"] is None

    # 3. Rate work
    rate_resp = client.post(
        f"/personal/records/{work_id}/rate",
        json={"rating": 9.5},
    )
    assert rate_resp.status_code == 200
    assert rate_resp.json()["user_rating"] == 9.5

    # 4. Toggle watchlist
    wl_resp = client.post(f"/personal/records/{work_id}/watchlist")
    assert wl_resp.status_code == 200
    assert wl_resp.json()["in_watchlist"] is True
    # Toggle back
    wl_resp2 = client.post(f"/personal/records/{work_id}/watchlist")
    assert wl_resp2.status_code == 200
    assert wl_resp2.json()["in_watchlist"] is False

    # 5. Toggle favorite
    fav_resp = client.post(f"/personal/records/{work_id}/favorite")
    assert fav_resp.status_code == 200
    assert fav_resp.json()["is_favorite"] is True

    # 6. Update personal notes
    patch_resp = client.patch(
        f"/personal/records/{work_id}",
        json={"personal_notes": "Essential 90s cinema."},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["personal_notes"] == "Essential 90s cinema."


def test_watch_diary_api_lifecycle(client: TestClient) -> None:
    # Add movie to library
    add_resp = client.post(
        "/library/items",
        json={"tmdb_id": 680, "work_type": "MOVIE"},
    )
    work_id = add_resp.json()["work"]["id"]

    # 1. Log viewing
    diary_resp = client.post(
        "/personal/diary",
        json={
            "work_id": work_id,
            "watched_date": "2026-10-14",
            "rating_at_time": 9.0,
            "review_text": "Timeless classic rewatched.",
            "liked": True,
        },
    )
    assert diary_resp.status_code == 201
    log_data = diary_resp.json()
    log_id = log_data["id"]
    assert log_data["work_id"] == work_id
    assert log_data["rating_at_time"] == 9.0
    assert log_data["liked"] is True

    # 2. Verify PersonalRecord updated automatically
    rec_resp = client.get(f"/personal/records/{work_id}")
    assert rec_resp.status_code == 200
    rec = rec_resp.json()
    assert rec["watch_status"] == "COMPLETED"
    assert rec["watch_count"] == 1
    assert rec["is_favorite"] is True
    assert rec["last_watched_at"] == "2026-10-14"

    # 3. List diary entries
    list_resp = client.get(f"/personal/diary?work_id={work_id}")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 4. Get individual diary entry
    get_resp = client.get(f"/personal/diary/{log_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == log_id

    # 5. Delete diary entry
    del_resp = client.delete(f"/personal/diary/{log_id}")
    assert del_resp.status_code == 204

    # Confirm watch count reset
    rec_after = client.get(f"/personal/records/{work_id}").json()
    assert rec_after["watch_count"] == 0
    assert rec_after["watch_status"] == "UNWATCHED"


def test_custom_shelves_api_lifecycle(client: TestClient) -> None:
    # Add movie to library
    add_resp = client.post(
        "/library/items",
        json={"tmdb_id": 680, "work_type": "MOVIE"},
    )
    work_id = add_resp.json()["work"]["id"]

    # 1. Create custom shelf
    shelf_resp = client.post(
        "/personal/shelves",
        json={
            "name": "Criterion & Classics",
            "description": "Essential classic cinema.",
        },
    )
    assert shelf_resp.status_code == 201
    shelf_data = shelf_resp.json()
    shelf_id = shelf_data["id"]
    assert shelf_data["name"] == "Criterion & Classics"
    assert shelf_data["slug"] == "criterion-classics"

    # 2. List shelves
    list_resp = client.get("/personal/shelves")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 3. Add work to shelf
    item_resp = client.post(
        f"/personal/shelves/{shelf_id}/items",
        json={
            "work_id": work_id,
            "rank_order": 1,
            "note": "Top tier crime drama",
        },
    )
    assert item_resp.status_code == 201
    assert item_resp.json()["work_id"] == work_id

    # 4. Get shelf detail by slug
    detail_resp = client.get(f"/personal/shelves/{shelf_data['slug']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["items_count"] == 1
    assert len(detail["items"]) == 1
    assert detail["items"][0]["work_title"] == "Pulp Fiction"

    # 5. Reorder shelf items
    reorder_resp = client.put(
        f"/personal/shelves/{shelf_id}/items/reorder",
        json={"work_ids": [work_id]},
    )
    assert reorder_resp.status_code == 200

    # 6. Remove item from shelf
    remove_resp = client.delete(f"/personal/shelves/{shelf_id}/items/{work_id}")
    assert remove_resp.status_code == 204

    # 7. Delete shelf
    del_shelf_resp = client.delete(f"/personal/shelves/{shelf_id}")
    assert del_shelf_resp.status_code == 204


def test_catalog_filtering_api(client: TestClient) -> None:
    # Add movie to library
    add_resp = client.post(
        "/library/items",
        json={"tmdb_id": 680, "work_type": "MOVIE"},
    )
    work_id = add_resp.json()["work"]["id"]

    # Mark as favorite and rate 9.5
    client.patch(
        f"/personal/records/{work_id}",
        json={
            "is_favorite": True,
            "user_rating": 9.5,
            "watch_status": "COMPLETED",
        },
    )

    # Filter by favorite
    filter_resp = client.get("/personal/works?is_favorite=true&min_rating=9.0")
    assert filter_resp.status_code == 200
    items = filter_resp.json()
    assert len(items) == 1
    assert items[0]["work_id"] == work_id
    assert items[0]["personal"]["user_rating"] == 9.5
    assert items[0]["personal"]["is_favorite"] is True
