"""Application bootstrap, dependency wiring, and lifecycle hooks."""

from sqlalchemy.orm import configure_mappers

from app.core.config import Settings
from app.core.logging import configure_logging, get_logger
from app.jobs.runner import get_job_runner

logger = get_logger(__name__)


def load_all_models() -> None:
    """Import all module models to populate the SQLAlchemy DeclarativeBase registry."""
    import app.modules.integrations.models
    import app.modules.library.models
    import app.modules.metadata.models
    import app.modules.personal.models
    import app.modules.playback.models
    import app.modules.sources.models  # noqa: F401

    configure_mappers()


def normalize_proxy_env() -> None:
    """Normalize SOCKS proxy schemes in environment variables for httpx compatibility."""
    import os

    for key in (
        "ALL_PROXY",
        "all_proxy",
        "HTTP_PROXY",
        "http_proxy",
        "HTTPS_PROXY",
        "https_proxy",
    ):
        val = os.environ.get(key)
        if val and val.startswith("socks://"):
            os.environ[key] = "socks5://" + val[len("socks://") :]


def startup_app(settings: Settings) -> None:
    """Initialize required local directories, logging, and background runners."""
    normalize_proxy_env()
    settings.ensure_directories()
    configure_logging(settings)
    load_all_models()
    if settings.scheduler_enabled:
        runner = get_job_runner(settings)
        runner.start()
    logger.info("Application startup complete", extra={"event": "app.started"})


def shutdown_app() -> None:
    """Gracefully stop background runners and release resources."""
    runner = get_job_runner()
    if runner.is_running:
        runner.stop()
    logger.info("Application shutdown complete", extra={"event": "app.stopped"})
