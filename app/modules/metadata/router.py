"""FastAPI HTTP endpoints for the metadata module."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.modules.metadata.models import CreditType, WorkType
from app.modules.metadata.schemas import (
    ExternalSearchResultResponse,
    IngestWorkRequest,
    MediaWorkDetailResponse,
    MediaWorkSummaryResponse,
    PersonDetailResponse,
)
from app.modules.metadata.service import MetadataService

router = APIRouter(prefix="/metadata", tags=["metadata"])


def get_metadata_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> MetadataService:
    """Dependency injector for MetadataService."""
    return MetadataService(session=session)


@router.get("/search", response_model=list[ExternalSearchResultResponse])
async def search_metadata(
    query: Annotated[
        str, Query(min_length=1, description="Movie or series title to search")
    ],
    service: Annotated[MetadataService, Depends(get_metadata_service)],
    year: Annotated[int | None, Query(description="Release year")] = None,
    work_type: Annotated[WorkType, Query(description="MOVIE or SHOW")] = WorkType.MOVIE,
) -> list[ExternalSearchResultResponse]:
    """Search external metadata provider (TMDB) for matching works."""
    results = await service.search_external(
        query=query,
        release_year=year,
        work_type=work_type,
    )
    return [
        ExternalSearchResultResponse(
            tmdb_id=r.tmdb_id,
            title=r.title,
            work_type=WorkType(r.work_type),
            original_title=r.original_title,
            release_year=r.release_year,
            overview=r.overview,
            poster_path=r.poster_path,
            vote_average=r.vote_average,
        )
        for r in results
    ]


@router.post("/ingest", response_model=MediaWorkDetailResponse, status_code=201)
async def ingest_work(
    request: IngestWorkRequest,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
) -> MediaWorkDetailResponse:
    """Ingest a work from TMDB/OMDb into the local catalog."""
    work = await service.get_or_ingest_work(
        tmdb_id=request.tmdb_id,
        work_type=request.work_type,
    )
    return MediaWorkDetailResponse.model_validate(work)


@router.get("/works", response_model=list[MediaWorkSummaryResponse])
def list_works(
    service: Annotated[MetadataService, Depends(get_metadata_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    work_type: Annotated[WorkType | None, Query()] = None,
    release_year: Annotated[int | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
) -> list[MediaWorkSummaryResponse]:
    """List catalog works with optional filtering."""
    works = service.list_works(
        limit=limit,
        offset=offset,
        work_type=work_type,
        release_year=release_year,
        search=search,
    )
    return [MediaWorkSummaryResponse.model_validate(w) for w in works]


@router.get("/works/{id}", response_model=MediaWorkDetailResponse)
def get_work_details(
    id: int,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
) -> MediaWorkDetailResponse:
    """Fetch complete details of a catalog work."""
    work = service.get_work(id)
    return MediaWorkDetailResponse.model_validate(work)


@router.get("/people/{id}", response_model=PersonDetailResponse)
def get_person(
    id: int,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
) -> PersonDetailResponse:
    """Fetch complete biographical details and categorized filmography of a person."""
    return service.get_person_details(id)


@router.get("/people/{id}/filmography", response_model=list[MediaWorkSummaryResponse])
def get_person_filmography(
    id: int,
    service: Annotated[MetadataService, Depends(get_metadata_service)],
    credit_type: Annotated[CreditType | None, Query()] = None,
    job: Annotated[str | None, Query()] = None,
) -> list[MediaWorkSummaryResponse]:
    """Fetch all works associated with a specific person."""
    works = service.get_person_filmography(
        person_id=id, credit_type=credit_type, job=job
    )
    return [MediaWorkSummaryResponse.model_validate(w) for w in works]

