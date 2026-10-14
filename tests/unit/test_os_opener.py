"""Unit tests for SystemFileOpener OS launcher."""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.adapters.player.launcher import SystemFileOpener
from app.core.errors import FileMissingError


def test_open_file_calls_os_launcher(tmp_path: Path) -> None:
    fake_file = tmp_path / "movie.mp4"
    fake_file.write_bytes(b"dummy video data")

    opener = SystemFileOpener()
    with patch("subprocess.Popen") as mock_popen:
        success = opener.open_file(str(fake_file))
        assert success is True
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert args[0][1] == str(fake_file.resolve())
        assert kwargs["start_new_session"] is True


def test_open_file_missing_raises_file_missing_error(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist.mkv"
    opener = SystemFileOpener()
    with pytest.raises(FileMissingError, match="Media file not found on disk"):
        opener.open_file(str(non_existent))


def test_open_folder_calls_os_launcher(tmp_path: Path) -> None:
    sub_dir = tmp_path / "videos"
    sub_dir.mkdir()

    opener = SystemFileOpener()
    with patch("subprocess.Popen") as mock_popen:
        success = opener.open_folder(str(sub_dir))
        assert success is True
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert args[0][1] == str(sub_dir.resolve())
        assert kwargs["start_new_session"] is True


def test_open_folder_missing_raises_file_missing_error(tmp_path: Path) -> None:
    non_existent = tmp_path / "no_such_folder"
    opener = SystemFileOpener()
    with pytest.raises(FileMissingError, match="Directory not found on disk"):
        opener.open_folder(str(non_existent))
