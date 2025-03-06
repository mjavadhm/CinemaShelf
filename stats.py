import json
from pathlib import Path
from collections import Counter

def collect_stats(json_file: Path, stats_file: Path) -> dict:
    """
    Collects statistics from movie data and saves them to a JSON file.
    
    Parameters:
    json_file (Path): Path to the JSON file containing movie data
    stats_file (Path): Path to save the statistics data
    
    Returns:
    dict: The collected statistics
    """
    # Create parent directories if they don't exist
    stats_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load movie data
    try:
        with json_file.open("r", encoding="utf-8") as f:
            movies_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        # Return default stats if movie data file doesn't exist or is invalid
        default_stats = {
            "movies": 0,
            "director": "N/A",
            "rating": 0.0,
            "decade": "N/A",
            "oldest_movie": "N/A",
            "newest_movie": "N/A",
            "genres": {}
        }
        save_stats(default_stats, stats_file)
        return default_stats
    
    # Initialize counters and aggregators
    director_count = Counter()
    genre_count = Counter()
    total_rating = 0.0
    valid_ratings = 0
    years = []
    decades = Counter()
    
    # Process each movie
    for movie in movies_data:
        data = movie.get("data", {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                continue
        
        # Extract director
        director_field = data.get("Director", "")
        if director_field and director_field != "N/A":
            # Count primary directors (first in the list if multiple)
            director = director_field.split(",")[0].strip()
            director_count[director] += 1
        
        # Extract rating
        try:
            imdb_rating = float(data.get("imdbRating", "0.0"))
            if imdb_rating > 0:
                total_rating += imdb_rating
                valid_ratings += 1
        except ValueError:
            pass
        
        # Extract year
        year_str = data.get("Year", "")
        from utils import extract_year
        year = extract_year(year_str)
        if year:
            years.append((year, data.get("Title", "Unknown")))
            decade = f"{(year // 10) * 10}s"
            decades[decade] += 1
        
        # Extract genres
        genres = data.get("Genre", "").split(", ")
        for genre in genres:
            if genre and genre != "N/A":
                genre_count[genre] += 1
    
    # Calculate statistics
    stats = {
        "movies": len(movies_data),
        "director": director_count.most_common(1)[0][0] if director_count else "N/A",
        "director_count": dict(director_count.most_common(5)),
        "rating": round(total_rating / valid_ratings, 1) if valid_ratings > 0 else 0.0,
        "decade": decades.most_common(1)[0][0] if decades else "N/A",
        "decade_distribution": dict(decades.most_common()),
        "oldest_movie": min(years)[1] if years else "N/A",
        "newest_movie": max(years)[1] if years else "N/A",
        "genres": dict(genre_count.most_common(5))
    }
    
    # Save statistics
    save_stats(stats, stats_file)
    return stats

def save_stats(stats: dict, stats_file: Path) -> None:
    """
    Saves statistics to a JSON file.
    
    Parameters:
    stats (dict): Statistics to save
    stats_file (Path): Path to save the statistics
    """
    with stats_file.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=4)

def load_stats(stats_file: Path) -> dict:
    """
    Loads statistics from a JSON file.
    
    Parameters:
    stats_file (Path): Path to the statistics file
    
    Returns:
    dict: The loaded statistics or default values if the file doesn't exist
    """
    if stats_file.exists():
        try:
            with stats_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    
    # Return default values if file doesn't exist or is invalid
    return {
        "movies": 0,
        "director": "N/A",
        "rating": 0.0,
        "decade": "N/A",
        "oldest_movie": "N/A",
        "newest_movie": "N/A",
        "genres": {}
    }