"""FastAPI HTTP endpoints for the integrations module."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import ApplicationError
from app.modules.integrations.models import IntegrationProvider, SyncRunStatus
from app.modules.integrations.schemas import (
    ConflictPolicy,
    ExternalItemMappingResponse,
    ImportSummaryResponse,
    RatingScaleMode,
    SyncRunResponse,
)
from app.modules.integrations.service import IntegrationsService

router = APIRouter(prefix="/integrations", tags=["integrations"])


def get_integrations_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> IntegrationsService:
    """Dependency provider for IntegrationsService."""
    return IntegrationsService(session)


@router.post(
    "/letterboxd/import-file",
    response_model=ImportSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Import Letterboxd export archive (.zip) or CSV file",
)
async def import_letterboxd_file(
    file: Annotated[
        UploadFile, File(description="Letterboxd CSV file or full ZIP export archive")
    ],
    service: Annotated[IntegrationsService, Depends(get_integrations_service)],
    conflict_policy: Annotated[
        ConflictPolicy, Form(description="PRESERVE_LOCAL or OVERWRITE_LOCAL")
    ] = ConflictPolicy.PRESERVE_LOCAL,
    scale_mode: Annotated[
        RatingScaleMode, Form(description="RAW (0.5-5.0) or TEN_POINT (1.0-10.0)")
    ] = RatingScaleMode.RAW,
) -> ImportSummaryResponse:
    """Ingest a Letterboxd ZIP archive or standalone CSV, synchronizing personal state and wanted items."""
    content = await file.read()
    filename = file.filename or "upload.csv"
    return await service.import_file(
        file_bytes=content,
        filename=filename,
        conflict_policy=conflict_policy,
        scale_mode=scale_mode,
    )


@router.get(
    "/sync-runs",
    response_model=list[SyncRunResponse],
    status_code=status.HTTP_200_OK,
    summary="List integration sync runs",
)
def list_sync_runs(
    service: Annotated[IntegrationsService, Depends(get_integrations_service)],
    provider: Annotated[
        IntegrationProvider | None, Query(description="Filter by provider")
    ] = None,
    status_filter: Annotated[
        SyncRunStatus | None, Query(alias="status", description="Filter by status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> list[SyncRunResponse]:
    """Retrieve audit history of integration synchronization runs."""
    runs = service.list_sync_runs(
        provider=provider,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [SyncRunResponse.model_validate(r) for r in runs]


@router.get(
    "/sync-runs/{run_id}",
    response_model=SyncRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed sync run by ID",
)
def get_sync_run(
    run_id: int,
    service: Annotated[IntegrationsService, Depends(get_integrations_service)],
) -> SyncRunResponse:
    """Retrieve a single synchronization execution record including error details."""
    run = service.get_sync_run(run_id)
    if run is None:
        raise ApplicationError(
            code="sync_run_not_found",
            message=f"Sync run {run_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return SyncRunResponse.model_validate(run)


@router.get(
    "/mappings",
    response_model=list[ExternalItemMappingResponse],
    status_code=status.HTTP_200_OK,
    summary="List external item mappings",
)
def list_mappings(
    service: Annotated[IntegrationsService, Depends(get_integrations_service)],
    provider: Annotated[
        IntegrationProvider | None, Query(description="Filter by provider")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> list[ExternalItemMappingResponse]:
    """List cached mappings connecting external identifiers to internal MediaWork entities."""
    mappings = service.list_mappings(
        provider=provider,
        limit=limit,
        offset=offset,
    )
    return [ExternalItemMappingResponse.model_validate(m) for m in mappings]
