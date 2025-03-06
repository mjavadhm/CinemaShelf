from pathlib import Path
import json
from mover import move_movies
from fetcher import fetch_movie_data
from categorizer import create_shortcuts_and_categorize

# Load configuration from JSON
CONFIG_FILE = Path("app_data/config.json")

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

config = load_config()

# Use config values
SOURCE_MOVIES = Path(config.get("SOURCE_MOVIES", "F:/Games/Film/movie"))
ALL_MOVIES = Path(config.get("ALL_MOVIES", "F:/Games/Film/AllMovies"))
JSON_FILE = Path(config.get("JSON_FILE", "movie_data.json"))
CATEGORIZED_DIR = Path(config.get("CATEGORIZED_DIR", "F:/Games/Film/Categorized"))
OMDB_API_KEY = config.get("OMDB_API_KEY", "71c04fc1")
FETCH_TYPE = config.get("FETCH_TYPE", 1)

def reload_config():
    global SOURCE_MOVIES, ALL_MOVIES, JSON_FILE, CATEGORIZED_DIR, OMDB_API_KEY ,FETCH_TYPE
    config = load_config()
    SOURCE_MOVIES = Path(config.get("SOURCE_MOVIES", "F:/Games/Film/movie"))
    ALL_MOVIES = Path(config.get("ALL_MOVIES", "F:/Games/Film/AllMovies"))
    JSON_FILE = Path(config.get("JSON_FILE", "movie_data.json"))
    CATEGORIZED_DIR = Path(config.get("CATEGORIZED_DIR", "F:/Games/Film/Categorized"))
    OMDB_API_KEY = config.get("OMDB_API_KEY", "71c04fc1")
    FETCH_TYPE = config.get("FETCH_TYPE", 1)

def main():
    print("Moving movie files...")
    move_movies(SOURCE_MOVIES, ALL_MOVIES)

    print("Fetching movie data...")
    fetch_movie_data(ALL_MOVIES, JSON_FILE, OMDB_API_KEY)

    print("Creating shortcuts and categorizing movies...")
    create_shortcuts_and_categorize(ALL_MOVIES, JSON_FILE, CATEGORIZED_DIR, True, True, True)



def main_move_movies():
    print(f"Moving movies from {SOURCE_MOVIES} to {ALL_MOVIES}")
    move_movies(SOURCE_MOVIES, ALL_MOVIES)

def main_fetch_movie_info(fetch_all):
    print(f"Fetching movie info using API Key: {OMDB_API_KEY}")
    fetch_movie_data(ALL_MOVIES, JSON_FILE, OMDB_API_KEY, fetch_all)

def main_categorize_movies(director, imdb, decade):
    print(f"Categorizing movies into {CATEGORIZED_DIR}")
    create_shortcuts_and_categorize(ALL_MOVIES, JSON_FILE, CATEGORIZED_DIR, director, imdb, decade)

if __name__ == "__main__":
    main()
