"""Application service and transaction orchestration for the metadata module."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.adapters.metadata_providers.client import (
    ExternalSearchResult,
    MetadataProvidersClient,
    MetadataProvidersPort,
)
from app.core.errors import ApplicationError
from app.modules.metadata.models import (
    CreditType,
    MediaEpisode,
    MediaSeason,
    MediaWork,
    WorkCredit,
    WorkGenre,
    WorkType,
)
from app.modules.metadata.repository import MetadataRepository
from app.modules.metadata.schemas import (
    PersonCreditDetailResponse,
    PersonDetailResponse,
)


class MetadataService:
    """Service layer coordinating metadata domain rules and transactions."""

    def __init__(
        self,
        session: Session,
        provider: MetadataProvidersPort | None = None,
    ) -> None:
        self.session = session
        self.repository = MetadataRepository(session)
        self.provider = provider or MetadataProvidersClient()

    async def search_external(
        self,
        query: str,
        release_year: int | None = None,
        work_type: WorkType = WorkType.MOVIE,
    ) -> list[ExternalSearchResult]:
        """Search external metadata provider for movies or TV shows."""
        return await self.provider.search(
            query=query,
            release_year=release_year,
            work_type=work_type.value,
        )

    async def get_or_ingest_work(
        self,
        tmdb_id: int,
        work_type: WorkType = WorkType.MOVIE,
    ) -> MediaWork:
        """Find existing MediaWork or fetch and persist from external provider."""
        existing = self.repository.get_work_by_tmdb_id(tmdb_id)
        if existing is not None:
            return existing

        details = await self.provider.fetch_details(tmdb_id, work_type=work_type.value)

        # 1. Instantiate MediaWork
        work = MediaWork(
            work_type=work_type,
            tmdb_id=details.tmdb_id,
            imdb_id=details.imdb_id,
            title=details.title,
            original_title=details.original_title,
            persian_title=details.persian_title,
            original_language=details.original_language,
            overview=details.overview,
            release_date=details.release_date,
            release_year=details.release_year,
            runtime_minutes=details.runtime_minutes,
            status=details.status,
            poster_path=details.poster_path,
            backdrop_path=details.backdrop_path,
            tmdb_rating=details.tmdb_rating,
            tmdb_vote_count=details.tmdb_vote_count,
            imdb_rating=details.imdb_rating,
            imdb_votes=details.imdb_votes,
            rotten_tomatoes_score=details.rotten_tomatoes_score,
            metascore=details.metascore,
            last_synced_at=datetime.now(UTC),
        )
        self.repository.create_work(work)

        # 2. Attach genres
        for g in details.genres:
            genre_entity = self.repository.get_or_create_genre(
                tmdb_genre_id=g.tmdb_genre_id,
                name=g.name,
                persian_name=g.persian_name,
            )
            work_genre = WorkGenre(work_id=work.id, genre_id=genre_entity.id)
            self.session.add(work_genre)

        # 3. Attach credits (Cast & Key Crew)
        for c in details.credits:
            person_entity = self.repository.get_or_create_person(
                tmdb_person_id=c.tmdb_person_id,
                name=c.name,
                imdb_person_id=c.imdb_person_id,
                original_name=c.original_name,
                known_for_department=c.known_for_department,
                profile_path=c.profile_path,
            )
            credit_type = (
                CreditType.CAST if c.credit_type == "CAST" else CreditType.CREW
            )
            work_credit = WorkCredit(
                work_id=work.id,
                person_id=person_entity.id,
                tmdb_credit_id=c.tmdb_credit_id,
                credit_type=credit_type,
                department=c.department,
                job=c.job,
                character_name=c.character_name,
                billing_order=c.billing_order,
            )
            self.session.add(work_credit)

        # 4. Attach seasons & episodes if SHOW
        for s in details.seasons:
            season_entity = MediaSeason(
                work_id=work.id,
                season_number=s.season_number,
                tmdb_season_id=s.tmdb_season_id,
                title=s.title,
                overview=s.overview,
                poster_path=s.poster_path,
                air_date=s.air_date,
                episode_count=s.episode_count,
            )
            self.session.add(season_entity)
            self.session.flush()

            for ep in s.episodes:
                episode_entity = MediaEpisode(
                    work_id=work.id,
                    season_id=season_entity.id,
                    season_number=ep.season_number,
                    episode_number=ep.episode_number,
                    tmdb_episode_id=ep.tmdb_episode_id,
                    title=ep.title,
                    overview=ep.overview,
                    air_date=ep.air_date,
                    runtime_minutes=ep.runtime_minutes,
                    still_path=ep.still_path,
                    tmdb_rating=ep.tmdb_rating,
                )
                self.session.add(episode_entity)

        self.session.commit()
        return self.get_work(work.id)

    def get_work(self, work_id: int) -> MediaWork:
        """Fetch MediaWork by ID or raise ApplicationError."""
        work = self.repository.get_work_by_id(work_id)
        if work is None:
            raise ApplicationError(
                code="work_not_found",
                message=f"MediaWork {work_id} not found",
                status_code=404,
            )
        return work

    def list_works(
        self,
        limit: int = 50,
        offset: int = 0,
        work_type: WorkType | None = None,
        release_year: int | None = None,
        search: str | None = None,
    ) -> Sequence[MediaWork]:
        """List works with filtering."""
        return self.repository.list_works(
            limit=limit,
            offset=offset,
            work_type=work_type,
            release_year=release_year,
            search=search,
        )

    def get_person_filmography(
        self,
        person_id: int,
        credit_type: CreditType | None = None,
        job: str | None = None,
    ) -> Sequence[MediaWork]:
        """Fetch all works associated with a person."""
        person = self.repository.get_person_by_id(person_id)
        if person is None:
            raise ApplicationError(
                code="person_not_found",
                message=f"Person {person_id} not found",
                status_code=404,
            )
        return self.repository.get_person_filmography(
            person_id=person_id,
            credit_type=credit_type,
            job=job,
        )

    def get_person_details(self, person_id: int) -> PersonDetailResponse:
        """Fetch Person and their categorized credits or raise 404."""
        person = self.repository.get_person_by_id(person_id)
        if person is None:
            raise ApplicationError(
                code="person_not_found",
                message=f"Person {person_id} not found",
                status_code=404,
            )
        credits = self.repository.get_person_credits(person_id)
        cast_credits = [c for c in credits if c.credit_type == CreditType.CAST]
        crew_credits = [c for c in credits if c.credit_type == CreditType.CREW]
        return PersonDetailResponse(
            id=person.id,
            tmdb_person_id=person.tmdb_person_id,
            name=person.name,
            original_name=person.original_name,
            persian_name=person.persian_name,
            known_for_department=person.known_for_department,
            profile_path=person.profile_path,
            cast=[PersonCreditDetailResponse.model_validate(c) for c in cast_credits],
            crew=[PersonCreditDetailResponse.model_validate(c) for c in crew_credits],
        )

