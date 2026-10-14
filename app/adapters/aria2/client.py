"""Adapter implementation: Aria2 JSON-RPC client adapter."""

import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import ProviderUnavailableError

logger = logging.getLogger(__name__)


@dataclass
class Aria2TaskStatus:
    """Status details of a specific download in Aria2."""

    gid: str
    status: str  # "active" | "waiting" | "paused" | "error" | "complete" | "removed"
    total_length_bytes: int = 0
    completed_length_bytes: int = 0
    download_speed_bps: int = 0
    progress_percent: float = 0.0
    file_path: str | None = None
    file_name: str | None = None
    error_message: str | None = None
    files: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_length(self) -> int:
        return self.total_length_bytes

    @property
    def completed_length(self) -> int:
        return self.completed_length_bytes

    @property
    def download_speed(self) -> int:
        return self.download_speed_bps


@dataclass
class Aria2GlobalStats:
    """Global performance and queue counters for Aria2."""

    download_speed_bps: int
    upload_speed_bps: int
    num_active: int
    num_waiting: int
    num_stopped: int

    @property
    def download_speed(self) -> int:
        return self.download_speed_bps

    @property
    def upload_speed(self) -> int:
        return self.upload_speed_bps


class Aria2Port(Protocol):
    """Protocol defining the interface for Aria2 integration."""

    def is_daemon_running(self) -> bool:
        """Check if Aria2 RPC daemon is responsive."""
        ...

    def start_local_daemon(self) -> bool:
        """Launch local aria2c daemon if available on the system."""
        ...

    def add_uri(
        self,
        url: str,
        destination_dir: str | None = None,
        file_name: str | None = None,
    ) -> str:
        """Enqueue a download URI in Aria2 and return the GID."""
        ...

    def tell_status(self, gid: str) -> Aria2TaskStatus:
        """Fetch current progress and state for a specific GID."""
        ...

    def tell_active(self) -> list[Aria2TaskStatus]:
        """Fetch all currently active downloads."""
        ...

    def pause(self, gid: str) -> bool:
        """Pause an active download."""
        ...

    def unpause(self, gid: str) -> bool:
        """Resume a paused download."""
        ...

    def remove(self, gid: str) -> bool:
        """Cancel and remove a download from Aria2."""
        ...

    def pause_all(self) -> bool:
        """Pause all ongoing downloads."""
        ...

    def resume_all(self) -> bool:
        """Resume all paused downloads."""
        ...

    def get_global_stats(self) -> Aria2GlobalStats:
        """Retrieve overall network and queue stats."""
        ...

    def get_global_stat(self) -> Aria2GlobalStats:
        """Alias for get_global_stats."""
        ...

    def set_speed_limit(self, limit_kb: int) -> bool:
        """Set maximum overall download speed in KB/s (0 for unlimited)."""
        ...

    def change_global_option(self, options: dict[str, str]) -> bool:
        """Change global Aria2 configuration options dynamically."""
        ...


class Aria2Client:
    """Synchronous client communicating with Aria2 via JSON-RPC 2.0 over HTTP."""

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http_client = http_client

    def _get_client(self) -> httpx.Client:
        if self._http_client is not None:
            return self._http_client
        return httpx.Client(timeout=10.0)

    def _build_payload(self, method: str, params: list[Any]) -> dict[str, Any]:
        full_params: list[Any] = []
        if self.settings.aria2_rpc_secret:
            full_params.append(f"token:{self.settings.aria2_rpc_secret}")
        full_params.extend(params)
        return {
            "jsonrpc": "2.0",
            "id": f"cinemashelf_{int(time.time() * 1000)}",
            "method": method,
            "params": full_params,
        }

    def _call(self, method: str, *params: Any) -> Any:
        client = self._get_client()
        payload = self._build_payload(method, list(params))
        should_close = self._http_client is None
        try:
            resp = client.post(self.settings.aria2_rpc_url, json=payload)
            if resp.status_code != 200:
                raise ProviderUnavailableError(
                    f"Aria2 RPC returned HTTP {resp.status_code}: {resp.text}"
                )
            data = resp.json()
            if "error" in data:
                err_msg = data["error"].get("message", "Unknown Aria2 error")
                raise ProviderUnavailableError(f"Aria2 RPC error ({method}): {err_msg}")
            return data.get("result")
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(
                f"Failed to connect to Aria2 RPC at {self.settings.aria2_rpc_url}: {exc}"
            ) from exc
        finally:
            if should_close:
                client.close()

    def is_daemon_running(self) -> bool:
        """Check if Aria2 daemon is answering getVersion."""
        try:
            self._call("aria2.getVersion")
            return True
        except Exception:  # noqa: BLE001
            return False

    def start_local_daemon(self) -> bool:
        """Start local aria2c background daemon if executable exists."""
        if not shutil.which("aria2c"):
            logger.warning("aria2c executable not found on system PATH")
            return False

        # Extract port from rpc url (default 6800)
        port = "6800"
        url = self.settings.aria2_rpc_url
        if ":" in url.split("/")[-2]:
            port = url.split("/")[-2].split(":")[-1]

        dl_dir = str(self.settings.download_dir.resolve())
        os.makedirs(dl_dir, exist_ok=True)

        cmd = [
            "aria2c",
            "--enable-rpc",
            "--rpc-listen-all=false",
            f"--rpc-listen-port={port}",
            f"--max-concurrent-downloads={self.settings.max_concurrent_downloads}",
            "--split=8",
            "--max-connection-per-server=8",
            "--continue=true",
            f"--dir={dl_dir}",
            "--daemon=true",
        ]
        if self.settings.aria2_rpc_secret:
            cmd.append(f"--rpc-secret={self.settings.aria2_rpc_secret}")

        try:
            subprocess.Popen(cmd)
            time.sleep(1.0)
            logger.info("Spawned local aria2c daemon on port %s", port)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to spawn aria2c process: %s", exc)
            return False

    def _parse_task_status(self, raw: dict[str, Any]) -> Aria2TaskStatus:
        gid = raw.get("gid", "")
        status = raw.get("status", "unknown")
        total = int(raw.get("totalLength", "0") or "0")
        completed = int(raw.get("completedLength", "0") or "0")
        speed = int(raw.get("downloadSpeed", "0") or "0")
        progress = round((completed / total) * 100, 1) if total > 0 else 0.0

        file_path = None
        file_name = None
        files = raw.get("files", [])
        if files:
            file_path = files[0].get("path")
            if file_path:
                file_name = Path(file_path).name

        err_msg = raw.get("errorMessage")

        return Aria2TaskStatus(
            gid=gid,
            status=status,
            total_length_bytes=total,
            completed_length_bytes=completed,
            download_speed_bps=speed,
            progress_percent=progress,
            file_path=file_path,
            file_name=file_name,
            error_message=err_msg,
            files=files,
        )

    def add_uri(
        self,
        url: str,
        destination_dir: str | None = None,
        file_name: str | None = None,
    ) -> str:
        """Enqueue download URI and return the GID."""
        options: dict[str, Any] = {}
        target_dir = destination_dir or str(self.settings.download_dir.resolve())
        options["dir"] = target_dir
        if file_name:
            options["out"] = file_name

        gid: str = self._call("aria2.addUri", [url], options)
        return gid

    def tell_status(self, gid: str) -> Aria2TaskStatus:
        """Fetch details of a single GID."""
        fields = [
            "gid",
            "status",
            "totalLength",
            "completedLength",
            "downloadSpeed",
            "files",
            "errorMessage",
        ]
        raw = self._call("aria2.tellStatus", gid, fields)
        return self._parse_task_status(raw)

    def tell_active(self) -> list[Aria2TaskStatus]:
        """Fetch status of all currently active tasks."""
        fields = [
            "gid",
            "status",
            "totalLength",
            "completedLength",
            "downloadSpeed",
            "files",
            "errorMessage",
        ]
        raw_list = self._call("aria2.tellActive", fields)
        return [self._parse_task_status(item) for item in raw_list]

    def pause(self, gid: str) -> bool:
        """Pause a specific download task."""
        try:
            self._call("aria2.pause", gid)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to pause Aria2 GID %s: %s", gid, exc)
            return False

    def unpause(self, gid: str) -> bool:
        """Resume a specific paused download task."""
        try:
            self._call("aria2.unpause", gid)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to unpause Aria2 GID %s: %s", gid, exc)
            return False

    def remove(self, gid: str) -> bool:
        """Remove a download task from Aria2."""
        try:
            self._call("aria2.remove", gid)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to remove Aria2 GID %s: %s", gid, exc)
            return False

    def pause_all(self) -> bool:
        """Pause all active tasks."""
        try:
            self._call("aria2.pauseAll")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to pauseAll in Aria2: %s", exc)
            return False

    def resume_all(self) -> bool:
        """Resume all paused tasks."""
        try:
            self._call("aria2.unpauseAll")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to unpauseAll in Aria2: %s", exc)
            return False

    def get_global_stats(self) -> Aria2GlobalStats:
        """Retrieve aggregated download/upload speeds and task counters."""
        raw = self._call("aria2.getGlobalStat")
        return Aria2GlobalStats(
            download_speed_bps=int(raw.get("downloadSpeed", "0") or "0"),
            upload_speed_bps=int(raw.get("uploadSpeed", "0") or "0"),
            num_active=int(raw.get("numActive", "0") or "0"),
            num_waiting=int(raw.get("numWaiting", "0") or "0"),
            num_stopped=int(raw.get("numStopped", "0") or "0"),
        )

    def get_global_stat(self) -> Aria2GlobalStats:
        """Alias for get_global_stats."""
        return self.get_global_stats()

    def set_speed_limit(self, limit_kb: int) -> bool:
        """Set maximum download bandwidth in KB/s (0 removes limit)."""
        limit_str = f"{limit_kb}K" if limit_kb > 0 else "0"
        return self.change_global_option({"max-overall-download-limit": limit_str})

    def change_global_option(self, options: dict[str, str]) -> bool:
        """Dynamically modify Aria2 global options."""
        try:
            self._call("aria2.changeGlobalOption", options)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to change Aria2 global options: %s", exc)
            return False
