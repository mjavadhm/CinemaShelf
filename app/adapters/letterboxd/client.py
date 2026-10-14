"""Adapter implementation: Letterboxd CSV parser and browser session extractor adapter."""

from typing import Protocol


class LetterboxdPort(Protocol):
    """Protocol contract for letterboxd integration."""
