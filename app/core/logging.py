"""Centralized standard logging configuration."""
import logging
from logging.handlers import RotatingFileHandler

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure root logger with console and rotating file handlers."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if root_logger.handlers:
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    settings.log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        settings.log_dir / "cinemashelf.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named module logger."""
    return logging.getLogger(name)
