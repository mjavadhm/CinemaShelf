"""Integration tests for Multi-Library management, directory browsing, and filesystem scanning."""

import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_create_and_list_libraries(client: TestClient):
    """Test creating a new named library and listing libraries."""
    lib_name = f"Lib_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/library/libraries",
        json={
            "name": lib_name,
            "content_type": "MOVIE",
            "preferred_language": "fa",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == lib_name
    assert data["content_type"] == "MOVIE"
    lib_id = data["id"]

    # List libraries
    resp_list = client.get("/api/library/libraries")
    assert resp_list.status_code == 200
    all_libs = resp_list.json()
    assert any(l["id"] == lib_id for l in all_libs)


def test_directory_browser(client: TestClient):
    """Test server filesystem directory browsing."""
    resp = client.get("/api/library/directories/browse")
    assert resp.status_code == 200
    data = resp.json()
    assert "current_path" in data
    assert "directories" in data
    assert isinstance(data["directories"], list)


def test_add_root_and_scan_filesystem(client: TestClient, tmp_path: Path):
    """Test creating a library, adding a real filesystem root, and scanning it."""
    # Create library
    lib_resp = client.post(
        "/api/library/libraries",
        json={"name": f"Library_{uuid.uuid4().hex[:8]}", "content_type": "MOVIE"},
    )
    assert lib_resp.status_code == 201
    lib_id = lib_resp.json()["id"]

    # Create dummy movie file in tmp_path: Inception.2010.1080p.BluRay.x265.mkv
    movie_file = tmp_path / "Inception.2010.1080p.BluRay.x265.mkv"
    movie_file.write_bytes(b"0" * (160 * 1024 * 1024))  # 160MB to pass size filter

    # Create dummy subtitle
    sub_file = tmp_path / "Inception.2010.1080p.BluRay.x265.srt"
    sub_file.write_text("1\n00:00:01,000 --> 00:00:04,000\nHello Inception\n")

    # Add root to library
    root_resp = client.post(
        f"/api/library/libraries/{lib_id}/roots",
        json={"label": "Test Root", "mount_path": str(tmp_path)},
    )
    assert root_resp.status_code == 201
    root_id = root_resp.json()["id"]

    # Trigger scan
    scan_resp = client.post(f"/api/library/libraries/{lib_id}/scan")
    assert scan_resp.status_code == 200
    scan_data = scan_resp.json()
    assert scan_data["status"] == "COMPLETED"
    assert scan_data["files_discovered"] >= 1
    assert scan_data["files_imported"] >= 1

    # Verify library item and membership
    lib_detail = client.get(f"/api/library/libraries/{lib_id}").json()
    assert lib_detail["movie_count"] >= 1
