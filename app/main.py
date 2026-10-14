"""FastAPI application entry point for CinemaShelf."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.bootstrap import shutdown_app, startup_app
from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.modules.downloads.router import router as downloads_router
from app.modules.integrations.router import router as integrations_router
from app.modules.library.router import router as library_router
from app.modules.metadata.router import router as metadata_router
from app.modules.personal.router import router as personal_router
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

    # Enable CORS for local frontend development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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

    # Consolidated API router mounted under /api
    api_router = APIRouter(prefix="/api")
    api_router.include_router(metadata_router)
    api_router.include_router(library_router)
    api_router.include_router(sources_router)
    api_router.include_router(playback_router)
    api_router.include_router(personal_router)
    api_router.include_router(integrations_router)
    api_router.include_router(downloads_router)

    app.include_router(api_router)

    # Direct mount routers for root paths and backwards compatibility
    app.include_router(metadata_router)
    app.include_router(library_router)
    app.include_router(sources_router)
    app.include_router(playback_router)
    app.include_router(personal_router)
    app.include_router(integrations_router)
    app.include_router(downloads_router)

    return app


app = create_app()
