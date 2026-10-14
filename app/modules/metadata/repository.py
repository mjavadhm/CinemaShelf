"""Persistence queries for the metadata module (no internal commits)."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.metadata.models import (
    CreditType,
    Genre,
    MediaSeason,
    MediaWork,
    Person,
    WorkCredit,
    WorkType,
)


class MetadataRepository:
    """Repository for metadata persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_work_by_id(self, work_id: int) -> MediaWork | None:
        """Fetch MediaWork by internal ID with relationships eagerly loaded."""
        stmt = (
            select(MediaWork)
            .where(MediaWork.id == work_id)
            .options(
                selectinload(MediaWork.genres),
                selectinload(MediaWork.credits).joinedload(WorkCredit.person),
                selectinload(MediaWork.seasons).selectinload(MediaSeason.episodes),
            )
        )
        return self.session.scalars(stmt).first()

    def get_work_by_tmdb_id(self, tmdb_id: int) -> MediaWork | None:
        """Fetch MediaWork by TMDB ID."""
        stmt = (
            select(MediaWork)
            .where(MediaWork.tmdb_id == tmdb_id)
            .options(
                selectinload(MediaWork.genres),
                selectinload(MediaWork.credits).joinedload(WorkCredit.person),
                selectinload(MediaWork.seasons).selectinload(MediaSeason.episodes),
            )
        )
        return self.session.scalars(stmt).first()

    def get_work_by_imdb_id(self, imdb_id: str) -> MediaWork | None:
        """Fetch MediaWork by IMDb ID."""
        stmt = (
            select(MediaWork)
            .where(MediaWork.imdb_id == imdb_id)
            .options(
                selectinload(MediaWork.genres),
                selectinload(MediaWork.credits).joinedload(WorkCredit.person),
                selectinload(MediaWork.seasons).selectinload(MediaSeason.episodes),
            )
        )
        return self.session.scalars(stmt).first()

    def list_works(
        self,
        limit: int = 50,
        offset: int = 0,
        work_type: WorkType | None = None,
        release_year: int | None = None,
        search: str | None = None,
    ) -> Sequence[MediaWork]:
        """List and filter catalog works."""
        stmt = select(MediaWork).order_by(MediaWork.id.desc())

        if work_type:
            stmt = stmt.where(MediaWork.work_type == work_type)
        if release_year:
            stmt = stmt.where(MediaWork.release_year == release_year)
        if search:
            stmt = stmt.where(MediaWork.title.ilike(f"%{search}%"))

        stmt = stmt.limit(limit).offset(offset)
        return self.session.scalars(stmt).all()

    def get_or_create_genre(
        self,
        tmdb_genre_id: int,
        name: str,
        persian_name: str | None = None,
    ) -> Genre:
        """Find or insert a genre."""
        genre = self.session.scalars(
            select(Genre).where(Genre.tmdb_genre_id == tmdb_genre_id)
        ).first()
        if genre is None:
            genre = Genre(
                tmdb_genre_id=tmdb_genre_id,
                name=name,
                persian_name=persian_name,
            )
            self.session.add(genre)
            self.session.flush()
        return genre

    def get_or_create_person(
        self,
        tmdb_person_id: int,
        name: str,
        imdb_person_id: str | None = None,
        original_name: str | None = None,
        persian_name: str | None = None,
        known_for_department: str | None = None,
        profile_path: str | None = None,
    ) -> Person:
        """Find or insert a Person."""
        person = self.session.scalars(
            select(Person).where(Person.tmdb_person_id == tmdb_person_id)
        ).first()
        if person is None:
            person = Person(
                tmdb_person_id=tmdb_person_id,
                imdb_person_id=imdb_person_id,
                name=name,
                original_name=original_name,
                persian_name=persian_name,
                known_for_department=known_for_department,
                profile_path=profile_path,
            )
            self.session.add(person)
            self.session.flush()
        else:
            # Update fields if new information arrived
            if profile_path and not person.profile_path:
                person.profile_path = profile_path
            if imdb_person_id and not person.imdb_person_id:
                person.imdb_person_id = imdb_person_id
        return person

    def create_work(self, work: MediaWork) -> MediaWork:
        """Add new MediaWork to session."""
        self.session.add(work)
        self.session.flush()
        return work

    def get_person_by_id(self, person_id: int) -> Person | None:
        """Fetch person by primary key."""
        return self.session.get(Person, person_id)

    def get_person_filmography(
        self,
        person_id: int,
        credit_type: CreditType | None = None,
        job: str | None = None,
    ) -> Sequence[MediaWork]:
        """Fetch all works associated with a person."""
        stmt = (
            select(MediaWork)
            .join(WorkCredit, WorkCredit.work_id == MediaWork.id)
            .where(WorkCredit.person_id == person_id)
            .distinct()
        )
        if credit_type:
            stmt = stmt.where(WorkCredit.credit_type == credit_type)
        if job:
            stmt = stmt.where(WorkCredit.job == job)

        return self.session.scalars(stmt).all()
