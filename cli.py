import click
import json
import os
import shutil
from pathlib import Path
from colorama import Fore, Style, init
from main import main_move_movies, main_fetch_movie_info, main_categorize_movies, reload_config
from fetcher import fetch_movie_data

init(autoreset=True)  # enable colors in terminal

CONFIG_FILE = Path("app_data/config.json")

ASCII_BANNER = f"""
{Fore.CYAN}     ▄████▄   ██▓ ███▄    █ ▓█████  ███▄ ▄███▓ ▄▄▄           ██████  ██░ ██ ▓█████  ██▓      █████▒
▒██▀ ▀█  ▓██▒ ██ ▀█   █ ▓█   ▀ ▓██▒▀█▀ ██▒▒████▄       ▒██    ▒ ▓██░ ██▒▓█   ▀ ▓██▒    ▓██   ▒ 
▒▓█    ▄ ▒██▒▓██  ▀█ ██▒▒███   ▓██    ▓██░▒██  ▀█▄     ░ ▓██▄   ▒██▀▀██░▒███   ▒██░    ▒████ ░ 
▒▓▓▄ ▄██▒░██░▓██▒  ▐▌██▒▒▓█  ▄ ▒██    ▒██ ░██▄▄▄▄██      ▒   ██▒░▓█ ░██ ▒▓█  ▄ ▒██░    ░▓█▒  ░ 
▒ ▓███▀ ░░██░▒██░   ▓██░░▒████▒▒██▒   ░██▒ ▓█   ▓██▒   ▒██████▒▒░▓█▒░██▓░▒████▒░██████▒░▒█░    
░ ░▒ ▒  ░░▓  ░ ▒░   ▒ ▒ ░░ ▒░ ░░ ▒░   ░  ░ ▒▒   ▓▒█░   ▒ ▒▓▒ ▒ ░ ▒ ░░▒░▒░░ ▒░ ░░ ▒░▓  ░ ▒ ░    
  ░  ▒    ▒ ░░ ░░   ░ ▒░ ░ ░  ░░  ░      ░  ▒   ▒▒ ░   ░ ░▒  ░ ░ ▒ ░▒░ ░ ░ ░  ░░ ░ ▒  ░ ░      
░         ▒ ░   ░   ░ ░    ░   ░      ░     ░   ▒      ░  ░  ░   ░  ░░ ░   ░     ░ ░    ░ ░    
░ ░       ░           ░    ░  ░       ░         ░  ░         ░   ░  ░  ░   ░  ░    ░  ░        
░                                                                                                
{Style.RESET_ALL}
"""

def center_text(text):
    columns = shutil.get_terminal_size().columns
    return "\n".join(line.center(columns) for line in text.split("\n"))

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def setup_config():
    click.echo(Fore.YELLOW + "Initial configuration is required. Please provide the following information:")
    source_movies = click.prompt("Path to the movies folder", default="F:/Games/Film/movie")
    all_movies = click.prompt("Path to the all movies folder", default="F:/Games/Film/AllMovies")
    categorized_dir = click.prompt("Path to the category folder", default="F:/Games/Film/AllMovies")
    json_file = click.prompt("Path to the JSON file", default="app_data/movie_data.json")
    omdb_api_key = click.prompt("OMDB API key", default="71c04fc1", hide_input=True)
    
    config = {
        "SOURCE_MOVIES": source_movies,
        "ALL_MOVIES": all_movies,
        "JSON_FILE": json_file,
        "CATEGORIZED_DIR": categorized_dir,
        "OMDB_API_KEY": omdb_api_key
    }
    save_config(config)
    reload_config()
    click.echo(Fore.GREEN + "Configuration saved!")
    return config

def main_menu():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        click.echo(center_text(ASCII_BANNER))
        click.echo(Fore.BLUE + "\nPlease choose an option:")
        click.echo("1 - Move movies to the central folder")
        click.echo("2 - Fetch movie information from the internet")
        click.echo("3 - Categorize movies")
        click.echo("4 - Change configuration")
        click.echo("0 - Exit")

        choice = click.prompt("Enter your choice", type=int)
        if choice == 1:
            click.echo(Fore.YELLOW + "Moving movies...")
            main_move_movies()
        elif choice == 2:
            fetch_movie_data_menu()
        elif choice == 3:
            click.echo(Fore.YELLOW + "Categorizing movies...")
            director = click.confirm("Do you want to categorize by director?", default=False)
            imdb = click.confirm("Do you want to categorize by IMDb rating?", default=False)
            decade = click.confirm("Do you want to categorize by production decade?", default=False)
            if not (director or imdb or decade):
                click.echo(Fore.RED + "No categorization option selected!")
                click.pause(Fore.YELLOW + "Press any key to continue...")
                continue
            main_categorize_movies(director, imdb, decade)
        elif choice == 4:
            update_config()
            
        elif choice == 0:
            click.echo(Fore.RED + "Goodbye!")
            break
        else:
            click.echo(Fore.RED + "Invalid option! Please try again.")
        click.pause(Fore.YELLOW + "Press any key to continue...")

def fetch_movie_data_menu():
    os.system("cls" if os.name == "nt" else "clear")
    click.echo(center_text(ASCII_BANNER))
    click.echo(Fore.BLUE + "\nPlease choose an option:")
    click.echo("1 - Fetch missing data")
    click.echo("2 - Reload all of the data")
    click.echo("3 - Main Menu")

    choice = click.prompt("Enter your choice", type=int)
    if choice == 1:
        click.echo(Fore.YELLOW + "Fetching movie information...")
        main_fetch_movie_info(False)
    elif choice == 2:
        click.echo(Fore.YELLOW + "Fetching movie information...")
        main_fetch_movie_info(True)
    elif choice == 3:
        main_menu()
    else:
        click.echo(Fore.RED + "Invalid option! Please try again.")

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    os.makedirs('app_data', exist_ok=True)
    
    config = load_config()
    if not config:
        config = setup_config()
    ctx.obj = config
    if ctx.invoked_subcommand is None:
        main_menu()

@cli.command()
def config():
    """Edit the configuration."""
    current_config = load_config()
    if not current_config:
        current_config = setup_config()
    else:
        click.echo(Fore.YELLOW + "Editing configuration:")
        current_config["SOURCE_MOVIES"] = click.prompt("Path to the movies folder", default=current_config.get("SOURCE_MOVIES", "F:/Games/Film/movie"))
        current_config["ALL_MOVIES"] = click.prompt("Path to the all movies folder", default=current_config.get("ALL_MOVIES", "F:/Games/Film/AllMovies"))
        current_config["JSON_FILE"] = click.prompt("Path to the JSON file", default=current_config.get("JSON_FILE", "app_data/movie_data.json"))
        current_config["CATEGORIZED_DIR"] = click.prompt("Path to the category folder", default=current_config.get("CATEGORIZED_DIR", "F:/Games/Film/AllMovies"))
        current_config["OMDB_API_KEY"] = click.prompt("OMDB API key", default=current_config.get("OMDB_API_KEY", "71c04fc1"), hide_input=True)
        save_config(current_config)
        reload_config()
        click.echo(Fore.GREEN + "Configuration updated!")
        return current_config

def update_config():
    """Edit the configuration."""
    current_config = load_config()
    if not current_config:
        current_config = setup_config()
    else:
        click.echo(Fore.YELLOW + "Editing configuration:")
        current_config["SOURCE_MOVIES"] = click.prompt("Path to the movies folder", default=current_config.get("SOURCE_MOVIES", "F:/Games/Film/movie"))
        current_config["ALL_MOVIES"] = click.prompt("Path to the all movies folder", default=current_config.get("ALL_MOVIES", "F:/Games/Film/AllMovies"))
        current_config["JSON_FILE"] = click.prompt("Path to the JSON file", default=current_config.get("JSON_FILE", "app_data/movie_data.json"))
        current_config["CATEGORIZED_DIR"] = click.prompt("Path to the category folder", default=current_config.get("CATEGORIZED_DIR", "F:/Games/Film/AllMovies"))
        current_config["OMDB_API_KEY"] = click.prompt("OMDB API key", default=current_config.get("OMDB_API_KEY", "71c04fc1"), hide_input=True)
        save_config(current_config)
        reload_config()
        click.echo(Fore.GREEN + "Configuration updated!")
        return current_config

if __name__ == '__main__':
    cli()
