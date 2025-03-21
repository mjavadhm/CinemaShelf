import re
from pathlib import Path

def sanitize_folder_name(name: str) -> str:
    """
    Replace invalid characters in folder names.
    Invalid characters: <>:"/\\|?*
    """
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def parse_movie_filename(file_name: str) -> tuple[str, str]:
    """
    Extracts the movie title and year from the file name.
    The algorithm considers the part before the first occurrence of a 4-digit year as the title.
    """
    base = Path(file_name).stem
    # Replace underscores and dots with spaces for easier matching.
    normalized = base.replace('_', ' ').replace('.', ' ')
    match = re.search(r'(18|19|20)\d{2}', normalized)
    if match:
        year = match.group(0)
        title = normalized[:match.start()].strip(' .-')
    else:
        year = ""
        title = normalized

    return title, year

def extract_year(year_str: str) -> int | None:
    """
    Extract the first 4-digit year from a string.
    """
    match = re.search(r'\b(19|20)\d{2}\b', year_str)
    if match:
        return int(match.group(0))
    return None
