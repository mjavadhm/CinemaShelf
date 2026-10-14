"""Safe OS file and directory opener adapter."""

import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Protocol

from app.core.errors import FileMissingError

logger = logging.getLogger(__name__)


class OSOpenerPort(Protocol):
    """Protocol for launching OS-level files and folders."""

    def open_file(self, file_path: str) -> bool:
        """Open a media file using the OS default application."""
        ...

    def open_folder(self, folder_path: str) -> bool:
        """Reveal a folder in the native OS file manager."""
        ...


class SystemFileOpener:
    """Safe, cross-platform file and folder launcher."""

    def open_file(self, file_path: str) -> bool:
        """Open the target file with the system default application."""
        target = Path(file_path).resolve()
        if not target.is_file():
            logger.warning("Target file does not exist on disk: %s", file_path)
            raise FileMissingError(f"Media file not found on disk: {file_path}")

        return self._launch(str(target))

    def open_folder(self, folder_path: str) -> bool:
        """Reveal directory in the OS file manager."""
        target = Path(folder_path).resolve()
        if not target.is_dir():
            logger.warning("Target directory does not exist on disk: %s", folder_path)
            raise FileMissingError(f"Directory not found on disk: {folder_path}")

        return self._launch(str(target))

    def _launch(self, path_str: str) -> bool:
        """Launch detached process via OS-specific handler."""
        current_os = platform.system()
        logger.info("Opening path on %s: %s", current_os, path_str)

        try:
            if current_os == "Windows":
                os.startfile(path_str)  # type: ignore[attr-defined]
                return True
            if current_os == "Darwin":
                cmd = ["open", path_str]
            else:
                # Linux / Unix default
                cmd = ["xdg-open", path_str]

            subprocess.Popen(
                cmd,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to launch %s with OS handler: %s", path_str, exc)
            return False
