import os
import shutil
from pathlib import Path
from utils import sanitize_folder_name, parse_movie_filename

def move_movies(source_folder: Path, destination_folder: Path) -> None:
    """
    Moves movie files from source_folder to destination_folder.
    Each movie file is placed in its own folder named after its sanitized title.
    """
    destination_folder.mkdir(parents=True, exist_ok=True)
    video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv')
    
    for root, _, files in os.walk(source_folder):
        for file in files:
            if file.lower().endswith(video_extensions):
                src_path = Path(root) / file
                title, _ = parse_movie_filename(file)
                safe_folder_name = sanitize_folder_name(title)
                new_dest_folder = destination_folder / safe_folder_name
                new_dest_folder.mkdir(parents=True, exist_ok=True)
                dest_path = new_dest_folder / file

                base = Path(file).stem
                ext = Path(file).suffix
                counter = 1
                while dest_path.exists():
                    new_file_name = f"{base}_{counter}{ext}"
                    dest_path = new_dest_folder / new_file_name
                    counter += 1

                print(f"Moving: {src_path} -> {dest_path}")
                shutil.move(str(src_path), str(dest_path))
    print("All movies have been moved.")
