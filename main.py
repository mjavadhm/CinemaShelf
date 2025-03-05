from pathlib import Path
from mover import move_movies
from fetcher import fetch_movie_data
from categorizer import create_shortcuts_and_categorize

def main():
    # Configuration (modify these paths as needed)
    SOURCE_MOVIES = Path("F:/Games/Film/movie")
    ALL_MOVIES = Path("F:/Games/Film/AllMovies")
    JSON_FILE = Path("movie_data.json")
    CATEGORIZED_DIR = Path("F:/Games/Film/Categorized")
    OMDB_API_KEY = "71c04fc1"

    print("Moving movie files...")
    move_movies(SOURCE_MOVIES, ALL_MOVIES)

    print("Fetching movie data...")
    fetch_movie_data(ALL_MOVIES, JSON_FILE, OMDB_API_KEY)

    print("Creating shortcuts and categorizing movies...")
    create_shortcuts_and_categorize(ALL_MOVIES, JSON_FILE, CATEGORIZED_DIR)

if __name__ == "__main__":
    main()
