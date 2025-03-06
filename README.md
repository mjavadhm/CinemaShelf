# CinemaShelf 🎬

CinemaShelf is a Python-based movie organizer tool that helps you manage and categorize your movie collection with ease. It moves movie files to a centralized folder, fetches movie information using the OMDb API, and creates shortcuts to categorize your movies by director, IMDb rating, and decade.

## Features

- **Move Movies:** Automatically transfers movie files from a source folder to a centralized folder, organizing each movie into its own directory.
- **Fetch Movie Data:** Retrieves detailed movie information from the OMDb API and stores it in a JSON file.
- **Categorize Movies:** Creates shortcuts for movies and categorizes them by director, IMDb rating, and decade.
- **User-Friendly CLI:** Interactive command-line interface with clear menus and color-coded messages.
- **Director Ranking:** Sorts directors by the number of movies they have in your collection.
- **Customizable Categories:** Choose which categories to create (director, IMDb rating, decade).

## Project Structure

```
CinemaShelf/
├── app_data/               # Directory for configuration and movie data
│   ├── config.json         # User configuration file
│   └── movie_data.json     # Movie metadata from OMDb API
├── categorizer.py          # Module for creating shortcuts and categorizing movies
├── cli.py                  # CLI interface and menu system
├── fetcher.py              # Module for fetching movie data from OMDb API
├── main.py                 # Main script to run the project
├── mover.py                # Module for moving movie files
├── setup.py                # Installation configuration
└── utils.py                # Utility functions for parsing and sanitizing movie data
```

## Requirements

- Python 3.8+
- Required libraries:
  - `requests` - For API calls
  - `pywin32` (only required on Windows) - For creating shortcuts
  - `click` - For the CLI interface
  - `colorama` - For terminal colors

Install the required packages using:

```bash
pip install requests pywin32 click colorama
```

Or install the package using:

```bash
pip install -e .
```

## Installation

Clone the repository and install the package:

```bash
git clone https://github.com/yourusername/cinemashelf.git
cd cinemashelf
pip install -e .
```

## Configuration

The application creates a configuration file at `app_data/config.json`. You can modify the following settings:

- `SOURCE_MOVIES`: Folder containing your original movie files
- `ALL_MOVIES`: Central folder where movie files will be moved
- `JSON_FILE`: File where fetched movie data will be stored
- `CATEGORIZED_DIR`: Base folder for categorized movie shortcuts
- `OMDB_API_KEY`: Your OMDb API key

You can update these settings through the configuration menu in the application.

## Usage

Run the application using:

```bash
python cli.py
```

The interactive menu will guide you through the following options:

1. **Move Movies**: Transfer movie files from the source folder to the central folder
2. **Fetch Movie Information**: 
   - Fetch missing data for new movies
   - Reload all movie data
3. **Categorize Movies**: Create shortcuts organized by:
   - Director (ranked by number of movies)
   - IMDb Rating
   - Release Decade
4. **Change Configuration**: Update application settings

### Movie Filename Format

The application works best when movie filenames include the title and release year in the format:
```
Movie Title (2023).mp4
```

The year helps improve accuracy when fetching movie data from the OMDb API.

## Categorization Details

### Director Category

Movies are organized by director, with folders named using a ranking system based on how many movies that director has in your collection:

```
/ByDirector/
  /1. Christopher Nolan/
    /Inception/
    /Interstellar/
  /2. Steven Spielberg/
    /Jurassic Park/
    /E.T./
```

### IMDb Rating Category

Movies are organized by their IMDb rating:

```
/ByIMDBRating/
  /8.5/
    /The Shawshank Redemption/
  /7.8/
    /The Avengers/
```

### Decade Category

Movies are organized by their release decade:

```
/ByDecade/
  /1990s/
    /Pulp Fiction/
  /2000s/
    /The Dark Knight/
```

## License

This project is licensed under the MIT License.
