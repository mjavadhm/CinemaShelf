# CinemaShelf 🎬

CinemaShelf is a Python-based movie organizer tool that helps you manage and categorize your movie collection with ease. It moves movie files to a centralized folder, fetches movie information using the OMDb API, and creates shortcuts to categorize your movies by director, IMDb rating, and decade.

## Features

- **Move Movies:** Automatically transfers movie files from a source folder to a centralized folder, organizing each movie into its own directory.
- **Fetch Movie Data:** Retrieves detailed movie information from the OMDb API and stores it in a JSON file.
- **Categorize Movies:** Creates shortcuts for movies and categorizes them by director, IMDb rating, and decade.

## Project Structure
```bash
CinemaShelf/
   ├── categorizer.py # Module for creating shortcuts and categorizing movies
   ├── fetcher.py # Module for fetching movie data from OMDb API
   ├── main.py # Main script to run the project
   ├── mover.py # Module for moving movie files
   └── utils.py # Utility functions for parsing and sanitizing movie data
```

## Requirements

- Python 3.8+
- Required libraries:
  - `requests`
  - `pywin32` (only required on Windows)

Install the required packages using:

```bash
pip install requests pywin32
```
##Configuration
All configuration is currently hard-coded in the main.py file.
Modify the following variables as needed:

- `SOURCE_MOVIES`: Folder containing your original movie files.
- `ALL_MOVIES`: Central folder where movie files will be moved.
- `JSON_FILE`: File where fetched movie data will be stored.
- `CATEGORIZED_DIR`: Base folder for categorized movie shortcuts.
- `OMDB_API_KEY`: Your OMDb API key.

##Usage
Simply run the main script:
```bash
python main.py
```
The script will execute the following steps:

Move Movies: Transfer movie files to the centralized folder.
Fetch Movie Data: Retrieve movie information from the OMDb API and save it to a JSON file.
Categorize Movies: Create shortcuts and organize movies by director, IMDb rating, and decade.
License
This project is licensed under the MIT License.

