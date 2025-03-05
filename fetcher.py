import json
import requests
from pathlib import Path
from utils import parse_movie_filename

def get_movie_info(title: str, year: str, api_key: str) -> dict:
    """
    Fetch movie information from the OMDb API.
    """
    url = f"http://www.omdbapi.com/?t={title}&y={year}&apikey={api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("Response", "False") == "True":
                return data
    except Exception as e:
        print(f"Error retrieving data for {title}: {e}")
    return {}

def fetch_movie_data(main_folder: Path, json_file: Path, api_key: str) -> None:
    """
    Scans the main_folder for movie files, fetches their data from OMDb,
    and stores the information in a JSON file.
    """
    # Load existing data if available
    if json_file.exists():
        with json_file.open("r", encoding="utf-8") as f:
            try:
                movies = json.load(f)
            except json.JSONDecodeError:
                movies = []
    else:
        movies = []

    video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv')
    movie_files = list(main_folder.rglob("*"))
    count = 0
    for file in movie_files:
        if file.is_file() and file.suffix.lower() in video_extensions:
            file_name = file.name
            # Skip if movie already exists in the JSON data
            if not any(movie.get("file_name") == file_name for movie in movies):
                count += 1
                print(f"Fetching data for: {file_name}")
                title, year = parse_movie_filename(file_name)
                data = get_movie_info(title, year, api_key)
                movies.append({
                    "file_name": file_name,
                    "data": data
                })
    print(f"Total movies processed: {len(movies)}")
    with json_file.open("w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=4)
    print("Movie data saved to JSON file.")
