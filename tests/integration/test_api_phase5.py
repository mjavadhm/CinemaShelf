"""Integration tests for Phase 5 Letterboxd File Imports & Integrations Endpoints."""

import io
import zipfile
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
from app.modules.integrations.router import get_integrations_service
from app.modules.integrations.service import IntegrationsService
from app.modules.metadata.models import MediaWork, WorkType
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
    personal_service = PersonalService(session=db_session)
    integrations_service = IntegrationsService(
        session=db_session,
        metadata_service=meta_service,
        personal_service=personal_service,
    )

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_metadata_service] = lambda: meta_service
    app.dependency_overrides[get_personal_service] = lambda: personal_service
    app.dependency_overrides[get_integrations_service] = lambda: integrations_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def preseeded_work(db_session: Session) -> MediaWork:
    work = MediaWork(
        work_type=WorkType.MOVIE,
        tmdb_id=680,
        title="Pulp Fiction",
        release_year=1994,
    )
    db_session.add(work)
    db_session.commit()
    return work


def test_import_csv_watchlist_endpoint(
    client: TestClient, preseeded_work: MediaWork
) -> None:
    csv_bytes = b"Date,Name,Year,Letterboxd URI\n2024-01-10,Pulp Fiction,1994,https://boxd.it/2a2a\n"
    files = {"file": ("watchlist.csv", io.BytesIO(csv_bytes), "text/csv")}

    resp = client.post("/integrations/letterboxd/import-file", files=files)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_items"] == 1
    assert data["watchlist_count"] == 1
    assert data["sync_run"]["status"] == "SUCCESS"

    # Verify personal record updated
    rec_resp = client.get(f"/personal/records/{preseeded_work.id}")
    assert rec_resp.status_code == 200
    assert rec_resp.json()["in_watchlist"] is True
    assert rec_resp.json()["watch_status"] == "WATCHLIST"


def test_import_zip_archive_endpoint(
    client: TestClient, preseeded_work: MediaWork
) -> None:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr(
            "ratings.csv",
            "Date,Name,Year,Letterboxd URI,Rating\n2024-02-01,Pulp Fiction,1994,https://boxd.it/2a2a,4.5\n",
        )

    files = {
        "file": ("export.zip", io.BytesIO(zip_buffer.getvalue()), "application/zip")
    }
    data_form = {
        "conflict_policy": "OVERWRITE_LOCAL",
        "scale_mode": "TEN_POINT",
    }

    resp = client.post(
        "/integrations/letterboxd/import-file",
        files=files,
        data=data_form,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ratings_count"] == 1
    assert data["sync_run"]["status"] == "SUCCESS"

    # 4.5 * 2 = 9.0 on ten-point scale
    rec_resp = client.get(f"/personal/records/{preseeded_work.id}")
    assert rec_resp.status_code == 200
    assert rec_resp.json()["user_rating"] == 9.0


def test_sync_runs_audit_endpoints(client: TestClient) -> None:
    # 1. Trigger an import so a run is logged
    csv_bytes = b"Date,Name,Year,Letterboxd URI\n2024-01-10,Pulp Fiction,1994,https://boxd.it/2a2a\n"
    files = {"file": ("watchlist.csv", io.BytesIO(csv_bytes), "text/csv")}
    client.post("/integrations/letterboxd/import-file", files=files)

    # 2. List sync runs
    list_resp = client.get("/integrations/sync-runs")
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert len(runs) >= 1
    run_id = runs[0]["id"]

    # 3. Get single sync run detail
    detail_resp = client.get(f"/integrations/sync-runs/{run_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == run_id
    assert detail_resp.json()["provider"] == "LETTERBOXD"

    # 4. Non-existent run
    missing_resp = client.get("/integrations/sync-runs/999999")
    assert missing_resp.status_code == 404


def test_mappings_endpoint(client: TestClient) -> None:
    csv_bytes = b"Date,Name,Year,Letterboxd URI\n2024-01-10,Pulp Fiction,1994,https://boxd.it/2a2a\n"
    files = {"file": ("watchlist.csv", io.BytesIO(csv_bytes), "text/csv")}
    client.post("/integrations/letterboxd/import-file", files=files)

    map_resp = client.get("/integrations/mappings")
    assert map_resp.status_code == 200
    mappings = map_resp.json()
    assert len(mappings) >= 1
    assert any(m["external_key"] == "https://boxd.it/2a2a" for m in mappings)
