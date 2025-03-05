import json
import platform
from pathlib import Path
from utils import sanitize_folder_name, extract_year

def create_shortcut(target: Path, shortcut_path: Path) -> None:
    """
    Creates a shortcut to the target file at shortcut_path.
    On Windows, uses win32com; on other OS, creates a symbolic link.
    """
    if platform.system() == "Windows":
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = str(target)
        shortcut.WorkingDirectory = str(target.parent)
        shortcut.save()
    else:
        shortcut_path.symlink_to(target)

def find_movie_file(file_name: str, search_folder: Path) -> Path | None:
    """
    Searches for the movie file with file_name in search_folder and its subdirectories.
    """
    for file in search_folder.rglob(file_name):
        if file.is_file():
            return file
    return None

def create_shortcuts_and_categorize(source_folder: Path, json_file: Path, dest_base: Path) -> None:
    """
    Creates shortcuts for movies and categorizes them by director, IMDb rating, and decade.
    """
    dest_base.mkdir(parents=True, exist_ok=True)
    with json_file.open("r", encoding="utf-8") as f:
        movies_data = json.load(f)

    director_groups = {}
    rating_groups = {}
    decade_groups = {}

    for movie in movies_data:
        file_name = movie.get("file_name", "")
        data = movie.get("data", {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                continue

        title = data.get("Title", "").strip()
        if not title:
            continue

        # Extract director (first director if multiple)
        director_field = data.get("Director", "")
        director = director_field.split(",")[0].strip() if director_field and director_field != "N/A" else "Unknown"

        # Extract IMDb rating
        try:
            imdb_rating = float(data.get("imdbRating", "0.0"))
        except ValueError:
            imdb_rating = 0.0

        # Extract year and calculate decade
        year_str = data.get("Year", "")
        year_int = extract_year(year_str) if year_str else None
        decade = f"{(year_int // 10) * 10}s" if year_int else "Unknown"

        director_groups.setdefault(director, []).append({
            "file_name": file_name,
            "title": title
        })
        rating_key = f"{imdb_rating:.1f}"
        rating_groups.setdefault(rating_key, []).append({
            "file_name": file_name,
            "title": title
        })
        decade_groups.setdefault(decade, []).append({
            "file_name": file_name,
            "title": title
        })

    # Categorize by Director
    director_folder_base = dest_base / "ByDirector"
    director_folder_base.mkdir(exist_ok=True)
    for director, movies in director_groups.items():
        safe_director = sanitize_folder_name(director)
        director_folder = director_folder_base / safe_director
        director_folder.mkdir(exist_ok=True)
        for movie in movies:
            safe_title = sanitize_folder_name(movie["title"])
            movie_folder = director_folder / safe_title
            movie_folder.mkdir(exist_ok=True)
            orig_path = find_movie_file(movie["file_name"], source_folder)
            if orig_path:
                shortcut_path = movie_folder / f"{safe_title}.lnk"
                create_shortcut(orig_path, shortcut_path)
                print(f"Director - Shortcut for '{movie['title']}' created at {shortcut_path}")
            else:
                print(f"Director - Original file for '{movie['title']}' not found.")

    # Categorize by IMDb Rating
    rating_folder_base = dest_base / "ByIMDBRating"
    rating_folder_base.mkdir(exist_ok=True)
    for rating, movies in rating_groups.items():
        safe_rating = sanitize_folder_name(rating)
        rating_folder = rating_folder_base / safe_rating
        rating_folder.mkdir(exist_ok=True)
        for movie in movies:
            safe_title = sanitize_folder_name(movie["title"])
            movie_folder = rating_folder / safe_title
            movie_folder.mkdir(exist_ok=True)
            orig_path = find_movie_file(movie["file_name"], source_folder)
            if orig_path:
                shortcut_path = movie_folder / f"{safe_title}.lnk"
                create_shortcut(orig_path, shortcut_path)
                print(f"IMDb - Shortcut for '{movie['title']}' created at {shortcut_path}")
            else:
                print(f"IMDb - Original file for '{movie['title']}' not found.")

    # Categorize by Decade
    decade_folder_base = dest_base / "ByDecade"
    decade_folder_base.mkdir(exist_ok=True)
    for decade, movies in decade_groups.items():
        safe_decade = sanitize_folder_name(decade)
        decade_folder = decade_folder_base / safe_decade
        decade_folder.mkdir(exist_ok=True)
        for movie in movies:
            safe_title = sanitize_folder_name(movie["title"])
            movie_folder = decade_folder / safe_title
            movie_folder.mkdir(exist_ok=True)
            orig_path = find_movie_file(movie["file_name"], source_folder)
            if orig_path:
                shortcut_path = movie_folder / f"{safe_title}.lnk"
                create_shortcut(orig_path, shortcut_path)
                print(f"Decade - Shortcut for '{movie['title']}' created at {shortcut_path}")
            else:
                print(f"Decade - Original file for '{movie['title']}' not found.")
