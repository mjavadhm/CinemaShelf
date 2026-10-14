"""Controlled background job runner and state machine definitions."""
from enum import StrEnum


class JobStatus(StrEnum):
    """Lifecycle states for long-running background jobs (see docs/05-workflows-and-jobs.md)."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
