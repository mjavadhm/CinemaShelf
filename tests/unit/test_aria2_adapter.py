"""Unit tests for the Aria2 JSON-RPC client adapter."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.adapters.aria2.client import (
    Aria2Client,
    Aria2GlobalStats,
    Aria2TaskStatus,
)
from app.core.config import Settings
from app.core.errors import ProviderUnavailableError


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        aria2_rpc_url="http://127.0.0.1:6800/jsonrpc",
        aria2_rpc_secret="testsecret",
    )


def test_aria2_payload_includes_secret(test_settings: Settings) -> None:
    client = Aria2Client(settings=test_settings)
    payload = client._build_payload("aria2.addUri", [["https://example.com/test.mp4"]])
    assert payload["method"] == "aria2.addUri"
    assert payload["params"][0] == "token:testsecret"
    assert payload["params"][1] == ["https://example.com/test.mp4"]


def test_aria2_add_uri_dispatches(test_settings: Settings) -> None:
    client = Aria2Client(settings=test_settings)
    with patch.object(client, "_call", return_value="1234567890abcdef") as mock_call:
        gid = client.add_uri(
            "https://example.com/movie.mp4", destination_dir="/downloads"
        )
        assert gid == "1234567890abcdef"
        mock_call.assert_called_once_with(
            "aria2.addUri",
            ["https://example.com/movie.mp4"],
            {"dir": "/downloads"},
        )


def test_aria2_tell_status_parsing(test_settings: Settings) -> None:
    client = Aria2Client(settings=test_settings)
    raw_status = {
        "gid": "test_gid_1",
        "status": "active",
        "totalLength": "1000000",
        "completedLength": "500000",
        "downloadSpeed": "102400",
        "uploadSpeed": "0",
        "files": [
            {
                "path": "/downloads/movie.mp4",
                "length": "1000000",
                "completedLength": "500000",
            }
        ],
        "errorMessage": "",
    }
    with patch.object(client, "_call", return_value=raw_status):
        status: Aria2TaskStatus = client.tell_status("test_gid_1")
        assert status.gid == "test_gid_1"
        assert status.status == "active"
        assert status.total_length == 1000000
        assert status.completed_length == 500000
        assert status.download_speed == 102400
        assert status.progress_percent == 50.0
        assert status.file_name == "movie.mp4"
        assert len(status.files) == 1


def test_aria2_get_global_stats(test_settings: Settings) -> None:
    client = Aria2Client(settings=test_settings)
    raw_stats = {
        "downloadSpeed": "512000",
        "uploadSpeed": "1024",
        "numActive": "2",
        "numWaiting": "3",
        "numStopped": "5",
    }
    with patch.object(client, "_call", return_value=raw_stats):
        stats: Aria2GlobalStats = client.get_global_stats()
        assert stats.download_speed == 512000
        assert stats.upload_speed == 1024
        assert stats.num_active == 2
        assert stats.num_waiting == 3
        assert stats.num_stopped == 5


def test_aria2_pause_and_unpause_and_remove(test_settings: Settings) -> None:
    client = Aria2Client(settings=test_settings)
    with patch.object(client, "_call", return_value="OK") as mock_call:
        assert client.pause("gid123") is True
        mock_call.assert_called_with("aria2.pause", "gid123")

        assert client.unpause("gid123") is True
        mock_call.assert_called_with("aria2.unpause", "gid123")

        assert client.remove("gid123") is True
        mock_call.assert_called_with("aria2.remove", "gid123")


def test_aria2_rpc_network_error_raises_provider_unavailable(
    test_settings: Settings,
) -> None:
    mock_http = MagicMock()
    mock_http.post.side_effect = httpx.ConnectError("Connection refused")
    client = Aria2Client(settings=test_settings, http_client=mock_http)
    with pytest.raises(
        ProviderUnavailableError, match="Failed to connect to Aria2 RPC"
    ):
        client._call("aria2.getVersion")


def test_aria2_rpc_error_response_raises_provider_unavailable(
    test_settings: Settings,
) -> None:
    mock_http = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "1",
        "error": {"code": 1, "message": "GID not found"},
    }
    mock_http.post.return_value = mock_resp
    client = Aria2Client(settings=test_settings, http_client=mock_http)
    with pytest.raises(ProviderUnavailableError, match="Aria2 RPC error"):
        client._call("aria2.tellStatus", "nonexistent_gid")
