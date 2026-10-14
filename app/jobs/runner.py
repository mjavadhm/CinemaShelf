"""Controlled background job runner and state machine definitions."""

import logging
import threading
from collections.abc import Callable
from enum import StrEnum

from sqlalchemy.orm import Session

from app.adapters.aria2.client import Aria2Client, Aria2Port
from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.jobs.handlers import (
    is_within_schedule,
    process_queued_downloads_jit,
    sync_active_downloads,
)
from app.modules.sources.service import SourcesService

logger = logging.getLogger(__name__)


class JobStatus(StrEnum):
    """Lifecycle states for long-running background jobs (see docs/05-workflows-and-jobs.md)."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class BackgroundJobRunner:
    """Daemon runner executing download sync and JIT night scheduler."""

    def __init__(
        self,
        settings: Settings | None = None,
        session_factory: Callable[[], Session] = SessionLocal,
        aria2_client: Aria2Port | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.session_factory = session_factory
        self.aria2 = aria2_client or Aria2Client(settings=self.settings)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        """Return True if background thread is active."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the background scheduler thread."""
        if self.is_running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="CinemaShelf-BackgroundJobRunner",
            daemon=True,
        )
        self._thread.start()
        logger.info("BackgroundJobRunner started.")

    def stop(self, timeout: float = 5.0) -> None:
        """Signal runner to stop and wait for completion."""
        if not self.is_running:
            return

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        logger.info("BackgroundJobRunner stopped.")

    def _run_loop(self) -> None:
        """Main periodic loop for download progress monitoring and JIT queueing."""
        logger.info(
            "JIT night scheduler loop started (Start: %d:00, End: %d:00, Poll: %ds).",
            self.settings.scheduler_start_hour,
            self.settings.scheduler_end_hour,
            self.settings.scheduler_poll_interval_seconds,
        )

        while not self._stop_event.is_set():
            try:
                self._run_iteration()
            except Exception as exc:  # noqa: BLE001
                logger.error("Unexpected error in background job loop: %s", exc)

            # Sleep until next poll or until stop is requested
            self._stop_event.wait(
                timeout=max(1, self.settings.scheduler_poll_interval_seconds)
            )

    def _run_iteration(self) -> None:
        """Single execution iteration."""
        if not self.settings.scheduler_enabled:
            return

        in_window = self.settings.scheduler_force_run or is_within_schedule(
            self.settings.scheduler_start_hour,
            self.settings.scheduler_end_hour,
        )

        session = self.session_factory()
        try:
            sources_service = SourcesService(
                session=session,
                aria2_client=self.aria2,
                settings=self.settings,
            )

            # 1. Always sync active downloads (update progress, detect completion)
            sync_active_downloads(session=session, aria2=self.aria2)

            # 2. If within night schedule, advance queued downloads into Aria2
            if in_window:
                process_queued_downloads_jit(
                    session=session,
                    sources_service=sources_service,
                    max_concurrent=self.settings.max_concurrent_downloads,
                )
        finally:
            session.close()


_runner_instance: BackgroundJobRunner | None = None
_runner_lock = threading.Lock()


def get_job_runner(settings: Settings | None = None) -> BackgroundJobRunner:
    """Provide singleton instance of BackgroundJobRunner."""
    global _runner_instance
    with _runner_lock:
        if _runner_instance is None:
            _runner_instance = BackgroundJobRunner(settings=settings)
        return _runner_instance
