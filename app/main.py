"""FastAPI application entry point for CinemaShelf."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.bootstrap import shutdown_app, startup_app
from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.modules.library.router import router as library_router
from app.modules.metadata.router import router as metadata_router
from app.modules.playback.router import router as playback_router
from app.modules.sources.router import router as sources_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage explicit application startup and shutdown lifecycle."""
    settings = get_settings()
    startup_app(settings)
    try:
        yield
    finally:
        shutdown_app()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()
    app = FastAPI(
        title="CinemaShelf",
        version="0.1.0",
        description="Local-first personal movie library and download manager",
        lifespan=lifespan,
    )

    @app.exception_handler(ApplicationError)
    async def application_error_handler(request, exc: ApplicationError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "environment": settings.app_env}

    app.include_router(metadata_router)
    app.include_router(library_router)
    app.include_router(sources_router)
    app.include_router(playback_router)

    return app


app = create_app()
