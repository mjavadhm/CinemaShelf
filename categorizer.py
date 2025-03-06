import json
import platform
import shutil
from pathlib import Path
from utils import sanitize_folder_name, extract_year
from colorama import Fore
from collections import Counter

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

def create_shortcuts_and_categorize(source_folder: Path, json_file: Path, dest_base: Path, need_director: bool, need_imdb: bool, need_decade: bool) -> None:
    """
    Creates shortcuts for movies and categorizes them by director, IMDb rating, and decade.
    Directors are sorted by movie count and folder names include ranking numbers.
    """
    dest_base.mkdir(parents=True, exist_ok=True)
    with json_file.open("r", encoding="utf-8") as f:
        movies_data = json.load(f)

    director_groups = {}
    rating_groups = {}
    decade_groups = {}
    director_movie_count = Counter()

    # First pass: count movies per director
    for movie in movies_data:
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
        
        # Count movies per director
        director_movie_count[director] += 1

    # Second pass: group movies and create shortcuts
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
        
        if need_director:
            director_groups.setdefault(director, []).append({
                "file_name": file_name,
                "title": title
            })
        if need_imdb:
            rating_key = f"{imdb_rating:.1f}"
            rating_groups.setdefault(rating_key, []).append({
                "file_name": file_name,
                "title": title
            })
        if need_decade:
            decade_groups.setdefault(decade, []).append({
                "file_name": file_name,
                "title": title
            })

    # Categorize by Director with ranking
    if need_director:
        director_folder_base = dest_base / "ByDirector"
        director_folder_base.mkdir(exist_ok=True)
        
        # If the directory already exists, remove it and recreate
        if director_folder_base.exists():
            shutil.rmtree(director_folder_base)
            director_folder_base.mkdir(exist_ok=True)
        
        # Create ranked director folders
        for rank, (director, _) in enumerate(director_movie_count.most_common(), 1):
            movies = director_groups.get(director, [])
            safe_director = sanitize_folder_name(director)
            # Create folder with rank prefix
            ranked_director_name = f"{rank}. {safe_director}"
            director_folder = director_folder_base / ranked_director_name
            director_folder.mkdir(exist_ok=True)
            
            for movie in movies:
                safe_title = sanitize_folder_name(movie["title"])
                movie_folder = director_folder / safe_title
                movie_folder.mkdir(exist_ok=True)
                orig_path = find_movie_file(movie["file_name"], source_folder)
                if orig_path:
                    shortcut_path = movie_folder / f"{safe_title}.lnk"
                    create_shortcut(orig_path, shortcut_path)
                    print(Fore.GREEN + f"Director - Shortcut for '{movie['title']}' created at {shortcut_path}")
                else:
                    print(Fore.RED + f"Director - Original file for '{movie['title']}' not found.")

    # Categorize by IMDb Rating
    if need_imdb:
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
                    print(Fore.GREEN + f"IMDb - Shortcut for '{movie['title']}' created at {shortcut_path}")
                else:
                    print(Fore.RED + f"IMDb - Original file for '{movie['title']}' not found.")

    # Categorize by Decade
    if need_decade:
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
                    print(Fore.GREEN + f"Decade - Shortcut for '{movie['title']}' created at {shortcut_path}")
                else:
                    print(Fore.RED + f"Decade - Original file for '{movie['title']}' not found.")