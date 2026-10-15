"""Integration tests for library analytics, statistics, and virtual categorization."""

import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.main import app
from app.modules.library.models import Library, LibraryContentType, LibraryItem, LibraryMembership, MediaFile
from app.modules.metadata.models import CreditType, Genre, MediaWork, Person, WorkCredit, WorkGenre, WorkType


def test_library_stats_and_categorize(db_session: Session, tmp_path: Path) -> None:
    app.dependency_overrides[get_db_session] = lambda: db_session
    client = TestClient(app)
    try:
        # 1. Create a Library
        lib = Library(
            name=f"Analytics Lib {tmp_path.name}",
            content_type=LibraryContentType.MOVIE,
        )
        db_session.add(lib)
        db_session.flush()

        # 2. Create Genre and Director
        genre = Genre(tmdb_genre_id=18, name="Drama", persian_name="درام")
        director = Person(
            tmdb_person_id=525,
            name="Christopher Nolan",
            persian_name="کریستوفر نولان",
        )
        db_session.add_all([genre, director])
        db_session.flush()

        # 3. Create MediaWork with credits and genre
        work = MediaWork(
            work_type=WorkType.MOVIE,
            tmdb_id=157336,
            title="Interstellar",
            persian_title="میان‌ستاره‌ای",
            release_year=2014,
            imdb_rating=8.7,
        )
        db_session.add(work)
        db_session.flush()

        # Associate genre and credit
        db_session.add(WorkGenre(work_id=work.id, genre_id=genre.id))
        db_session.add(
            WorkCredit(
                work_id=work.id,
                person_id=director.id,
                credit_type=CreditType.CREW,
                department="Directing",
                job="Director",
            )
        )

        # Create dummy movie file on disk
        movie_file = tmp_path / "Interstellar.2014.1080p.mkv"
        movie_file.write_bytes(b"dummy mkv video content")

        # Create LibraryItem and MediaFile
        item = LibraryItem(work_id=work.id)
        db_session.add(item)
        db_session.flush()

        db_session.add(
            LibraryMembership(library_id=lib.id, work_id=work.id)
        )

        media_file = MediaFile(
            library_item_id=item.id,
            file_path=str(movie_file),
            file_name=movie_file.name,
            file_size_bytes=movie_file.stat().st_size,
            resolution="1080p",
        )
        db_session.add(media_file)
        db_session.commit()

        # --- Test GET /api/library/stats ---
        resp = client.get("/api/library/stats")
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["total_movies"] >= 1
        assert stats["total_files"] >= 1
        assert stats["average_rating"] > 0.0
        assert any(d["name"] == "Christopher Nolan" for d in stats["top_directors"])
        assert "2010s" in stats["decade_distribution"]
        assert stats["newest_movie"] is not None

        # --- Test POST /api/library/categorize ---
        cat_dest = tmp_path / "virtual_shortcuts"
        cat_resp = client.post(
            "/api/library/categorize",
            json={
                "destination_path": str(cat_dest),
                "library_id": lib.id,
                "by_director": True,
                "by_rating": True,
                "by_decade": True,
            },
        )
        assert cat_resp.status_code == 200
        cat_data = cat_resp.json()
        assert cat_data["shortcuts_created"] >= 3
        assert "ByDirector" in cat_data["categories"]
        assert "ByRating" in cat_data["categories"]
        assert "ByDecade" in cat_data["categories"]

        # Verify shortcuts exist on disk
        by_director_dir = cat_dest / "ByDirector"
        assert by_director_dir.is_dir()
        subdirs = list(by_director_dir.iterdir())
        assert any("Christopher Nolan" in d.name for d in subdirs)
    finally:
        app.dependency_overrides.clear()
