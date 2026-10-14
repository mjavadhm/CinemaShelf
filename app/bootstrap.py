"""Application bootstrap, dependency wiring, and lifecycle hooks."""
from app.core.config import Settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def startup_app(settings: Settings) -> None:
    """Initialize required local directories, logging, and database state."""
    settings.ensure_directories()
    configure_logging(settings)
    logger.info("Application startup complete", extra={"event": "app.started"})


def shutdown_app() -> None:
    """Gracefully stop background runners and release resources."""
    logger.info("Application shutdown complete", extra={"event": "app.stopped"})
