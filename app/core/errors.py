"""Centralized application exception hierarchy and stable error codes."""


class ApplicationError(Exception):
    """Base class for expected application-level errors."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class SourceUnavailableError(ApplicationError):
    """Raised when a configured media source root is offline or unreachable."""

    def __init__(self, message: str = "منبع در دسترس نیست") -> None:
        super().__init__(code="source_unavailable", message=message, status_code=404)


class FileMissingError(ApplicationError):
    """Raised when a media file is missing on an online source."""

    def __init__(self, message: str = "فایل در منبع متصل پیدا نشد") -> None:
        super().__init__(code="file_missing", message=message, status_code=404)


class MatchAmbiguousError(ApplicationError):
    """Raised when movie identification produces multiple uncertain matches."""

    def __init__(self, message: str = "تطبیق فیلم مبهم است و نیاز به انتخاب دستی دارد") -> None:
        super().__init__(code="match_ambiguous", message=message, status_code=409)


class JobConflictError(ApplicationError):
    """Raised when an incompatible background job is already running."""

    def __init__(self, message: str = "عملیات مشابهی در حال اجراست") -> None:
        super().__init__(code="job_conflict", message=message, status_code=409)


class ProviderUnavailableError(ApplicationError):
    """Raised when an external provider (OMDb, Zarfilm, Aria2) is unreachable."""

    def __init__(self, message: str = "سرویس خارجی در دسترس نیست") -> None:
        super().__init__(code="provider_unavailable", message=message, status_code=503)
