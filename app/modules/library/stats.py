"""Library statistics and analytics calculator."""

from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.modules.library.models import LibraryItem, MediaFile
from app.modules.metadata.models import MediaWork, WorkCredit


def calculate_library_stats(session: Session, library_id: int | None = None) -> dict[str, Any]:
    """Calculate rich analytics across cataloged library items."""
    stmt = (
        select(LibraryItem)
        .options(
            joinedload(LibraryItem.work).selectinload(MediaWork.credits).joinedload(WorkCredit.person),
            joinedload(LibraryItem.work).selectinload(MediaWork.genres),
            selectinload(LibraryItem.media_files),
        )
    )
    if library_id is not None:
        from app.modules.library.models import LibraryMembership

        stmt = stmt.join(
            LibraryMembership, LibraryMembership.work_id == LibraryItem.work_id
        ).where(LibraryMembership.library_id == library_id)

    items = session.scalars(stmt).unique().all()

    if not items:
        return {
            "total_movies": 0,
            "total_files": 0,
            "total_size_bytes": 0,
            "average_rating": 0.0,
            "top_directors": [],
            "decade_distribution": {},
            "genre_distribution": {},
            "oldest_movie": None,
            "newest_movie": None,
        }

    total_movies = len(items)
    total_files = sum(len(item.media_files) for item in items)
    total_size_bytes = sum(
        sum(f.file_size_bytes or 0 for f in item.media_files) for item in items
    )

    ratings: list[float] = []
    director_counter: Counter[str] = Counter()
    decade_counter: Counter[str] = Counter()
    genre_counter: Counter[str] = Counter()

    movies_with_year: list[tuple[int, MediaWork]] = []

    for item in items:
        work = item.work
        if not work:
            continue

        rating = work.imdb_rating or work.tmdb_rating
        if rating and rating > 0:
            ratings.append(float(rating))

        if work.release_year:
            movies_with_year.append((work.release_year, work))
            decade = f"{(work.release_year // 10) * 10}s"
            decade_counter[decade] += 1

        for g in work.genres or []:
            genre_name = g.persian_name or g.name
            if genre_name:
                genre_counter[genre_name] += 1

        for credit in work.credits or []:
            if (
                credit.job
                and credit.job.lower() == "director"
                and credit.person
                and credit.person.name
            ):
                director_counter[credit.person.name] += 1

    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0

    oldest_movie = None
    newest_movie = None
    if movies_with_year:
        movies_with_year.sort(key=lambda x: x[0])
        oldest = movies_with_year[0][1]
        newest = movies_with_year[-1][1]
        oldest_movie = {
            "id": oldest.id,
            "title": oldest.persian_title or oldest.title,
            "release_year": oldest.release_year,
        }
        newest_movie = {
            "id": newest.id,
            "title": newest.persian_title or newest.title,
            "release_year": newest.release_year,
        }

    top_directors = [
        {"name": name, "count": count}
        for name, count in director_counter.most_common(5)
    ]

    return {
        "total_movies": total_movies,
        "total_files": total_files,
        "total_size_bytes": total_size_bytes,
        "average_rating": avg_rating,
        "top_directors": top_directors,
        "decade_distribution": dict(decade_counter.most_common()),
        "genre_distribution": dict(genre_counter.most_common(10)),
        "oldest_movie": oldest_movie,
        "newest_movie": newest_movie,
    }
