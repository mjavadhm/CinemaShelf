"""Adapter implementation: External movie metadata and poster provider adapter (port from `legacy/cinemashelf/fetcher.py`)."""
from typing import Protocol


class MetadataProvidersPort(Protocol):
    """Protocol contract for metadata_providers integration."""

    ...
