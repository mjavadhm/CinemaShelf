from pathlib import Path
import os
import sys
import json
import logging
from mover import move_movies
from fetcher import fetch_movie_data
from categorizer import create_shortcuts_and_categorize
from stats import collect_stats, load_stats

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration from JSON
CONFIG_FILE = Path("app_data/config.json")
STATS_FILE = Path("app_data/stats.json")

def get_appdata_path():
    """ پیدا کردن مسیر صحیح و ساخت خودکار app_data در اولین اجرا """
    if getattr(sys, 'frozen', False):  # اگر برنامه در حالت exe اجرا شود
        base_path = os.path.dirname(sys.executable)  # مسیر کنار فایل exe
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))  # مسیر اسکریپت Python

    appdata_path = os.path.join(base_path, "app_data")

    # اگر پوشه وجود نداشت، آن را بساز
    if not os.path.exists(appdata_path):
        os.makedirs(appdata_path)
        print(f"📁 پوشه app_data ساخته شد: {appdata_path}")

get_appdata_path()

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

config = load_config()

# Use config values
SOURCE_MOVIES = Path(config.get("SOURCE_MOVIES"))
ALL_MOVIES = Path(config.get("ALL_MOVIES"))
JSON_FILE = Path(config.get("JSON_FILE"))
CATEGORIZED_DIR = Path(config.get("CATEGORIZED_DIR"))
OMDB_API_KEY = config.get("OMDB_API_KEY", "71c04fc1")  # Default API key remains unchanged
FETCH_TYPE = config.get("FETCH_TYPE", 1)

def reload_config():
    global SOURCE_MOVIES, ALL_MOVIES, JSON_FILE, CATEGORIZED_DIR, OMDB_API_KEY, FETCH_TYPE
    config = load_config()
    SOURCE_MOVIES = Path(config.get("SOURCE_MOVIES"))
    ALL_MOVIES = Path(config.get("ALL_MOVIES"))
    JSON_FILE = Path(config.get("JSON_FILE"))
    CATEGORIZED_DIR = Path(config.get("CATEGORIZED_DIR"))
    OMDB_API_KEY = config.get("OMDB_API_KEY", "71c04fc1")
    FETCH_TYPE = config.get("FETCH_TYPE", 1)

def reload_stats():
    """
    Reloads the movie statistics from the JSON data and updates the stats file.
    
    Returns:
    dict: The updated statistics
    """
    return collect_stats(JSON_FILE, STATS_FILE)

def get_stats():
    """
    Gets the latest statistics or generates them if not available.
    
    Returns:
    dict: The current statistics
    """
    stats = load_stats(STATS_FILE)
    
    if stats.get("movies", 0) == 0 and JSON_FILE.exists():
        stats = reload_stats()
    return stats

def main():
    try:
        print("Moving movie files...")
        move_movies(SOURCE_MOVIES, ALL_MOVIES)
    except Exception as e:
        print(f"Error moving movies: {e}")
        logger.error(f"Error moving movies: {e}")

    try:
        print("Fetching movie data...")
        fetch_movie_data(ALL_MOVIES, JSON_FILE, OMDB_API_KEY, False)
    except Exception as e:
        print(f"Error fetching movie data: {e}")
        logger.error(f"Error fetching movie data: {e}")

    try:
        print("Creating shortcuts and categorizing movies...")
        create_shortcuts_and_categorize(ALL_MOVIES, JSON_FILE, CATEGORIZED_DIR, True, True, True)
    except Exception as e:
        print(f"Error creating shortcuts and categorizing movies: {e}")
        logger.error(f"Error creating shortcuts and categorizing movies: {e}")

    print("Updating statistics...")
    stats = reload_stats()
    print(f"Total movies: {stats['movies']}")
    print(f"Most movies by director: {stats['director']}")
    print(f"Average rating: {stats['rating']}")

def main_move_movies():
    print(f"Moving movies from {SOURCE_MOVIES} to {ALL_MOVIES}")
    move_movies(SOURCE_MOVIES, ALL_MOVIES)
    reload_stats()

def main_fetch_movie_info(fetch_all):
    print(f"Fetching movie info using API Key: {OMDB_API_KEY}")
    fetch_movie_data(ALL_MOVIES, JSON_FILE, OMDB_API_KEY, fetch_all)
    reload_stats()

def main_categorize_movies(director, imdb, decade):
    print(f"Categorizing movies into {CATEGORIZED_DIR}")
    create_shortcuts_and_categorize(ALL_MOVIES, JSON_FILE, CATEGORIZED_DIR, director, imdb, decade)
    reload_stats()

if __name__ == "__main__":
    main()
