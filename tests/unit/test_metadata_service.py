"""Unit tests for MetadataService."""

from datetime import date
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.orm import Session

from app.adapters.metadata_providers.client import (
    ExternalCredit,
    ExternalGenre,
    ExternalSearchResult,
    ExternalWorkDetails,
    MetadataProvidersPort,
)
from app.core.errors import ApplicationError
from app.modules.metadata.models import CreditType, WorkType
from app.modules.metadata.service import MetadataService


@pytest.fixture
def sample_details() -> ExternalWorkDetails:
    """Fixture providing parsed external work details."""
    return ExternalWorkDetails(
        tmdb_id=157336,
        work_type="MOVIE",
        title="Interstellar",
        imdb_id="tt0816692",
        original_title="Interstellar",
        overview="A team of explorers travel through a wormhole...",
        release_date=date(2014, 11, 7),
        release_year=2014,
        runtime_minutes=169,
        status="Released",
        tmdb_rating=8.4,
        imdb_rating=8.7,
        genres=[ExternalGenre(tmdb_genre_id=878, name="Science Fiction")],
        credits=[
            ExternalCredit(
                tmdb_person_id=525,
                name="Christopher Nolan",
                credit_type="CREW",
                department="Directing",
                job="Director",
            ),
            ExternalCredit(
                tmdb_person_id=10297,
                name="Matthew McConaughey",
                credit_type="CAST",
                department="Acting",
                job="Actor",
                character_name="Cooper",
                billing_order=0,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_search_delegates_to_provider(db_session: Session) -> None:
    """Verify search_external forwards query parameters to external provider."""
    mock_provider = AsyncMock(spec=MetadataProvidersPort)
    mock_provider.search.return_value = [
        ExternalSearchResult(
            tmdb_id=157336,
            title="Interstellar",
            work_type="MOVIE",
            release_year=2014,
        )
    ]

    service = MetadataService(session=db_session, provider=mock_provider)
    results = await service.search_external("Interstellar", release_year=2014)

    assert len(results) == 1
    assert results[0].title == "Interstellar"
    mock_provider.search.assert_awaited_once_with(
        query="Interstellar",
        release_year=2014,
        work_type="MOVIE",
    )


@pytest.mark.asyncio
async def test_get_or_ingest_work_idempotent(
    db_session: Session, sample_details: ExternalWorkDetails
) -> None:
    """Verify work is saved and subsequent calls do not re-fetch from external API."""
    mock_provider = AsyncMock(spec=MetadataProvidersPort)
    mock_provider.fetch_details.return_value = sample_details

    service = MetadataService(session=db_session, provider=mock_provider)

    # First call: fetches from provider and persists
    work1 = await service.get_or_ingest_work(tmdb_id=157336, work_type=WorkType.MOVIE)
    assert work1.id is not None
    assert work1.title == "Interstellar"
    assert len(work1.genres) == 1
    assert len(work1.credits) == 2
    assert mock_provider.fetch_details.call_count == 1

    # Second call: retrieves from DB directly
    work2 = await service.get_or_ingest_work(tmdb_id=157336, work_type=WorkType.MOVIE)
    assert work2.id == work1.id
    assert mock_provider.fetch_details.call_count == 1


def test_get_work_not_found_raises(db_session: Session) -> None:
    """Verify requesting non-existent work raises ApplicationError with 404."""
    service = MetadataService(session=db_session)
    with pytest.raises(ApplicationError) as exc_info:
        service.get_work(999999)
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "work_not_found"


@pytest.mark.asyncio
async def test_person_filmography_query(
    db_session: Session, sample_details: ExternalWorkDetails
) -> None:
    """Verify filmography lookup for a director/actor."""
    mock_provider = AsyncMock(spec=MetadataProvidersPort)
    mock_provider.fetch_details.return_value = sample_details
    service = MetadataService(session=db_session, provider=mock_provider)

    work = await service.get_or_ingest_work(tmdb_id=157336)
    nolan_credit = next(c for c in work.credits if c.job == "Director")

    filmography = service.get_person_filmography(
        person_id=nolan_credit.person_id,
        credit_type=CreditType.CREW,
        job="Director",
    )
    assert len(filmography) == 1
    assert filmography[0].title == "Interstellar"
