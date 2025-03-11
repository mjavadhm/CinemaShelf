import sys
import json
import os
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QFileDialog, QCheckBox, QMessageBox, QTabWidget,
                            QProgressBar, QGroupBox, QFormLayout, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QPixmap
from PyQt5 import QtGui
from qdarkstyle import load_stylesheet_pyqt5  # Import QDarkStyle for dark mode


import requests
from colorama import init, Fore
import io
import sys

# Import your existing modules
from mover import move_movies
from fetcher import fetch_movie_data
from categorizer import create_shortcuts_and_categorize
from main import reload_config, reload_stats, reload_stats, get_stats

# Initialize colorama
init(autoreset=True)

CONFIG_FILE = Path("app_data/config.json")
STATS_FILE = Path("app_data/stats.json")

class LogRedirector(io.StringIO):
    """Class to redirect stdout to a signal and convert ANSI colors to HTML for QTextEdit"""
    def __init__(self, signal_func):
        super(LogRedirector, self).__init__()
        self.signal_func = signal_func
        self.ansi_color_map = {
            # Regular colors
            '30': 'black',
            '31': 'red',
            '32': 'green',
            '33': 'orange',
            '34': 'blue',
            '35': 'purple',
            '36': 'cyan',
            '37': 'lightgray',
            # Bright colors
            '90': 'darkgray',
            '91': 'lightred',
            '92': 'lightgreen',
            '93': 'yellow',
            '94': 'lightblue',
            '95': 'lightpurple',
            '96': 'lightcyan',
            '97': 'white',
        }
        self.buffer = ""
        
    def write(self, text):
        if text.strip():  # Only emit non-empty strings
            # Convert ANSI to HTML
            html_text = self.ansi_to_html(text)
            if html_text:
                self.signal_func.emit(html_text)
        return len(text)
    
    def ansi_to_html(self, text):
        """Convert ANSI color codes to HTML tags"""
        result = ""
        i = 0
        length = len(text)
        
        while i < length:
            if text[i:i+2] == '\x1b[':
                # Found an ANSI escape sequence
                j = i + 2
                # Find the end of the sequence (usually 'm')
                while j < length and text[j] not in 'mK':
                    j += 1
                
                if j < length:
                    # Extract the code
                    code = text[i+2:j]
                    codes = code.split(';')
                    
                    # Process color codes
                    for c in codes:
                        if c in self.ansi_color_map:
                            result += f'<span style="color:{self.ansi_color_map[c]};">'
                        elif c == '0':  # Reset
                            result += '</span>'
                    
                    i = j + 1
                    continue
            
            result += text[i]
            i += 1
            
        return result

# Also modify the update_log methods to handle HTML
# def update_move_log(self, text):
#     self.move_log.insertHtml(text + "<br>")
#     self.move_log.ensureCursorVisible()

# def update_fetch_log(self, text):
#     self.fetch_log.insertHtml(text + "<br>")
#     self.fetch_log.ensureCursorVisible()
    
# def update_cat_log(self, text):
#     self.cat_log.insertHtml(text + "<br>")
#     self.cat_log.ensureCursorVisible()
    

class WorkerThread(QThread):
    """Worker thread for background operations"""
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)
    
    def __init__(self, task, *args):
        super().__init__()
        self.task = task
        self.args = args
        
    def run(self):
        # Redirect stdout to our signal
        original_stdout = sys.stdout
        sys.stdout = LogRedirector(self.update_signal)
        
        try:
            self.task(*self.args)
            self.finished_signal.emit(True)
        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")
            self.finished_signal.emit(False)
        finally:
            # Restore stdout
            sys.stdout = original_stdout

class CinemaShelfGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_config()
        
    def initUI(self):
        # Window settings
        self.setWindowTitle("CinemaShelf 🎬")
        
        # Custom modern stylesheet
        base_style = """
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: none;
                background-color: #2d2d2d;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #383838;
                color: #ffffff;
                padding: 8px 16px;
                margin: 2px;
                border: none;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
            QTabBar::tab:hover:!selected {
                background-color: #424242;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                margin: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1084d8;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background-color: #006cbd;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
                transform: translateY(1px);
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
            QLineEdit {
                padding: 6px;
                border: 1px solid #424242;
                border-radius: 4px;
                background-color: #2d2d2d;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
            QGroupBox {
                background-color: #2d2d2d;
                border: none;
                border-radius: 8px;
                margin-top: 12px;
                padding: 12px;
            }
            QGroupBox::title {
                color: #ffffff;
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 5px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #424242;
                border-radius: 4px;
                padding: 4px;
                color: #ffffff;
            }
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #2d2d2d;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 4px;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 1px solid #424242;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: none;
            }
            QLabel {
                color: #ffffff;
            }
        """
        self.setStyleSheet(base_style)
        self.setMinimumSize(900, 700)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Header with logo
        header_container = QWidget()
        header_container.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-radius: 8px;
                margin: 8px;
                padding: 16px;
            }
        """)
        header_layout = QVBoxLayout()
        
        header = QLabel("CinemaShelf 🎬")
        header.setFont(QFont("Segoe UI", 28, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #0078d4;")
        
        subtitle = QLabel("Your Personal Movie Collection Manager")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #cccccc;")
        
        header_layout.addWidget(header)
        header_layout.addWidget(subtitle)
        header_container.setLayout(header_layout)
        main_layout.addWidget(header_container)
        
        # Tab widget to organize features
        tabs = QTabWidget()
        
        # Create tabs
        self.home_tab = QWidget()
        self.move_tab = QWidget()
        self.fetch_tab = QWidget()
        self.categorize_tab = QWidget()
        self.settings_tab = QWidget()
        
        # Setup each tab
        self.setup_home_tab()
        self.setup_move_tab()
        self.setup_fetch_tab()
        self.setup_categorize_tab()
        self.setup_settings_tab()
        
        # Add tabs to tab widget
        tabs.addTab(self.home_tab, "Home")
        tabs.addTab(self.move_tab, "Move Movies")
        tabs.addTab(self.fetch_tab, "Fetch Info")
        tabs.addTab(self.categorize_tab, "Categorize")
        tabs.addTab(self.settings_tab, "Settings")
        
        main_layout.addWidget(tabs)
        
        # Status bar
        self.status = QLabel("Ready")
        self.status.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status)
        
        # Set layout
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
    def setup_home_tab(self):
        layout = QVBoxLayout()
        
        # Welcome message
        welcome = QLabel("Welcome to CinemaShelf")
        welcome.setFont(QFont("Arial", 16))
        welcome.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome)
        
        # Description
        description = QLabel(
            "CinemaShelf is a movie organizer tool that helps you manage and categorize "
            "your movie collection. Use the tabs above to navigate through the features."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)
        
        # Quick action buttons
        # quick_actions = QGroupBox("Quick Actions")
        # quick_layout = QHBoxLayout()
        
        # move_btn = QPushButton("Move Movies")
        # move_btn.clicked.connect(lambda: self.tabWidget().setCurrentIndex(1))
        
        # fetch_btn = QPushButton("Fetch Movie Info")
        # fetch_btn.clicked.connect(lambda: self.tabWidget().setCurrentIndex(2))
        
        # categorize_btn = QPushButton("Categorize Movies")
        # categorize_btn.clicked.connect(lambda: self.tabWidget().setCurrentIndex(3))
        
        # quick_layout.addWidget(move_btn)
        # quick_layout.addWidget(fetch_btn)
        # quick_layout.addWidget(categorize_btn)
        
        # quick_actions.setLayout(quick_layout)
        # layout.addWidget(quick_actions)
        
        # Stats section (can be populated later with actual data)
        stats = QGroupBox("Collection Statistics")
        stats_layout = QFormLayout()
        self.movies_label = QLabel("")
        self.director_label = QLabel("")
        self.rating_label = QLabel("")
        self.oldest_movie_label = QLabel("")
        self.newest_movie_label = QLabel("")
        
        self.reload_stats_button()
        stats_layout.addRow("Movies in collection:", self.movies_label)
        stats_layout.addRow("Top director:", self.director_label)
        stats_layout.addRow("Average IMDb rating:", self.rating_label)
        stats_layout.addRow("Oldest movie:", self.oldest_movie_label)
        stats_layout.addRow("Newest movie:", self.newest_movie_label)
        
        reload_stat_btn = QPushButton("Reload stats")
        reload_stat_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4f4f4f;
            }
        """)
        reload_stat_btn.clicked.connect(self.reload_stats_button)
        stats.setLayout(stats_layout)
        stats_layout.addWidget(reload_stat_btn)
        layout.addWidget(stats)
        
        self.home_tab.setLayout(layout)
        
    def setup_move_tab(self):
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "This feature moves your movie files from the source folder to a central "
            "organized folder. Each movie will be placed in its own directory."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Settings preview
        settings_preview = QGroupBox("Current Settings")
        preview_layout = QFormLayout()
        
        self.move_source_label = QLabel("")
        self.move_dest_label = QLabel("")
        
        preview_layout.addRow("Source folder:", self.move_source_label)
        preview_layout.addRow("Destination folder:", self.move_dest_label)
        
        settings_preview.setLayout(preview_layout)
        layout.addWidget(settings_preview)
        
        # Progress reporting
        self.move_progress = QProgressBar()
        self.move_progress.setVisible(False)
        layout.addWidget(self.move_progress)
        
        # Log group box
        log_group = QGroupBox("Operation Log")
        log_layout = QVBoxLayout()
        
        self.move_log = QTextEdit()
        self.move_log.setReadOnly(True)
        log_layout.addWidget(self.move_log)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Action button
        self.move_button = QPushButton("Start Moving Movies")
        self.move_button.setStyleSheet("""
            background-color: #4CAF50;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
            margin: 4px;
            min-width: 120px;
            transition: all 0.2s ease-in-out;
        """)  # Green color for move action
        self.move_button.setIcon(QIcon("app_data/icons/move_icon.png"))  # Add move icon from correct location
        self.move_button.setToolTip("Start moving movies")  # Add tooltip for better UX

        self.move_button.clicked.connect(self.start_move_movies)
        layout.addWidget(self.move_button)
        
        self.move_tab.setLayout(layout)
        
    def setup_fetch_tab(self):
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "This feature fetches movie information from the OMDb API for the movies "
            "in your collection. Choose whether to fetch only missing data or reload all."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Settings preview
        settings_preview = QGroupBox("Current Settings")
        preview_layout = QFormLayout()
        
        self.fetch_movies_dir_label = QLabel("")
        self.fetch_json_file_label = QLabel("")
        self.fetch_api_key_label = QLabel("")
        
        preview_layout.addRow("Movies directory:", self.fetch_movies_dir_label)
        preview_layout.addRow("JSON data file:", self.fetch_json_file_label)
        preview_layout.addRow("OMDb API key:", self.fetch_api_key_label)
        
        settings_preview.setLayout(preview_layout)
        layout.addWidget(settings_preview)
        
        # Options
        fetch_options = QGroupBox("Fetch Options")
        options_layout = QVBoxLayout()
        
        self.fetch_missing_only = QCheckBox("Fetch missing data only")
        self.fetch_missing_only.setChecked(True)
        
        options_layout.addWidget(self.fetch_missing_only)
        fetch_options.setLayout(options_layout)
        layout.addWidget(fetch_options)
        
        # Progress reporting
        self.fetch_progress = QProgressBar()
        self.fetch_progress.setVisible(False)
        layout.addWidget(self.fetch_progress)
        
        # Log group box
        log_group = QGroupBox("Operation Log")
        log_layout = QVBoxLayout()
        
        self.fetch_log = QTextEdit()
        self.fetch_log.setReadOnly(True)
        log_layout.addWidget(self.fetch_log)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Action button
        self.fetch_button = QPushButton("Start Fetching Movie Info")
        self.fetch_button.setStyleSheet("""
            background-color: #2196F3;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
            margin: 4px;
            min-width: 120px;
            transition: all 0.2s ease-in-out;
        """)  # Blue color for fetch action
        self.fetch_button.setIcon(QIcon("app_data/icons/fetch_icon.png"))  # Add fetch icon from correct location

        self.fetch_button.clicked.connect(self.start_fetch_movie_info)
        layout.addWidget(self.fetch_button)
        
        self.fetch_tab.setLayout(layout)
        
    def setup_categorize_tab(self):
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "This feature creates shortcuts to your movies and organizes them by "
            "director, IMDb rating, and decade. Choose which categories to create."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Settings preview
        settings_preview = QGroupBox("Current Settings")
        preview_layout = QFormLayout()
        
        self.cat_movies_dir_label = QLabel("")
        self.cat_json_file_label = QLabel("")
        self.cat_output_dir_label = QLabel("")
        
        preview_layout.addRow("Movies directory:", self.cat_movies_dir_label)
        preview_layout.addRow("JSON data file:", self.cat_json_file_label)
        preview_layout.addRow("Categorized output:", self.cat_output_dir_label)
        
        settings_preview.setLayout(preview_layout)
        layout.addWidget(settings_preview)
        
        # Options
        cat_options = QGroupBox("Categorization Options")
        options_layout = QVBoxLayout()
        
        self.cat_by_director = QCheckBox("Categorize by Director")
        self.cat_by_director.setChecked(True)
        
        self.cat_by_imdb = QCheckBox("Categorize by IMDb Rating")
        self.cat_by_imdb.setChecked(True)
        
        self.cat_by_decade = QCheckBox("Categorize by Decade")
        self.cat_by_decade.setChecked(True)
        
        options_layout.addWidget(self.cat_by_director)
        options_layout.addWidget(self.cat_by_imdb)
        options_layout.addWidget(self.cat_by_decade)
        
        cat_options.setLayout(options_layout)
        layout.addWidget(cat_options)
        
        # Progress reporting
        self.cat_progress = QProgressBar()
        self.cat_progress.setVisible(False)
        layout.addWidget(self.cat_progress)
        
        # Log group box
        log_group = QGroupBox("Operation Log")
        log_layout = QVBoxLayout()
        
        self.cat_log = QTextEdit()
        self.cat_log.setReadOnly(True)
        log_layout.addWidget(self.cat_log)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Action button
        self.cat_button = QPushButton("Start Categorizing Movies")
        self.cat_button.setStyleSheet("""
            background-color: #FF9800;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
            margin: 4px;
            min-width: 120px;
            transition: all 0.2s ease-in-out;
        """)  # Orange color for categorize action
        self.cat_button.setIcon(QIcon("app_data/icons/categorize_icon.png"))  # Add categorize icon from correct location

        self.cat_button.clicked.connect(self.start_categorize_movies)
        layout.addWidget(self.cat_button)
        
        self.categorize_tab.setLayout(layout)
        
    def setup_settings_tab(self):
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        # Source folder
        self.source_folder_input = QLineEdit()
        browse_source = QPushButton("Browse...")
        browse_source.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4f4f4f;
            }
        """)
        browse_source.clicked.connect(lambda: self.browse_folder(self.source_folder_input))
        
        source_layout = QHBoxLayout()
        source_layout.addWidget(self.source_folder_input)
        source_layout.addWidget(browse_source)
        
        form_layout.addRow("Source folder:", source_layout)
        
        # All movies folder
        self.all_movies_input = QLineEdit()
        browse_all = QPushButton("Browse...")
        browse_all.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4f4f4f;
            }
        """)
        browse_all.clicked.connect(lambda: self.browse_folder(self.all_movies_input))
        
        all_layout = QHBoxLayout()
        all_layout.addWidget(self.all_movies_input)
        all_layout.addWidget(browse_all)
        
        form_layout.addRow("All movies folder:", all_layout)
        
        # JSON file
        self.json_file_input = QLineEdit()
        browse_json = QPushButton("Browse...")
        browse_json.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4f4f4f;
            }
        """)
        browse_json.clicked.connect(lambda: self.browse_file(self.json_file_input))
        
        json_layout = QHBoxLayout()
        json_layout.addWidget(self.json_file_input)
        json_layout.addWidget(browse_json)
        
        form_layout.addRow("JSON data file:", json_layout)
        
        # Categorized directory
        self.categorized_dir_input = QLineEdit()
        browse_cat = QPushButton("Browse...")
        browse_cat.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4f4f4f;
            }
        """)
        browse_cat.clicked.connect(lambda: self.browse_folder(self.categorized_dir_input))
        
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(self.categorized_dir_input)
        cat_layout.addWidget(browse_cat)
        
        form_layout.addRow("Categorized folder:", cat_layout)
        
        # OMDB API key
        self.api_key_input = QLineEdit()
        form_layout.addRow("OMDb API key:", self.api_key_input)
        
        settings_group = QGroupBox("Configuration Settings")
        settings_group.setLayout(form_layout)
        layout.addWidget(settings_group)
        
        # Save button
        save_button = QPushButton("Save Configuration")
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                padding: 12px 24px;
                min-width: 120px;
                transition: all 0.2s ease-in-out;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
        """)
        save_button.clicked.connect(self.save_config)
        layout.addWidget(save_button)
        
        self.settings_tab.setLayout(layout)
        
    def browse_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            line_edit.setText(folder)
            
    def browse_file(self, line_edit):
        file, _ = QFileDialog.getOpenFileName(self, "Select File", "", "JSON Files (*.json)")
        if file:
            line_edit.setText(file)
            
    def load_config(self):  # Load configuration settings from JSON file

        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        else:
            config = {
                "SOURCE_MOVIES": "",
                "ALL_MOVIES": "",
                "JSON_FILE": "app_data/movie_data.json",
                "CATEGORIZED_DIR": "",
                "OMDB_API_KEY": ""
            }
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
        
        # Update UI with config values
        self.source_folder_input.setText(config.get("SOURCE_MOVIES", ""))
        self.all_movies_input.setText(config.get("ALL_MOVIES", ""))
        self.json_file_input.setText(config.get("JSON_FILE", "app_data/movie_data.json"))
        self.categorized_dir_input.setText(config.get("CATEGORIZED_DIR", ""))
        self.api_key_input.setText(config.get("OMDB_API_KEY", ""))
        
        # Update labels in other tabs
        self.update_settings_labels()
        
    def save_config(self):  # Save configuration settings to JSON file

        config = {
            "SOURCE_MOVIES": self.source_folder_input.text(),
            "ALL_MOVIES": self.all_movies_input.text(),
            "JSON_FILE": self.json_file_input.text(),
            "CATEGORIZED_DIR": self.categorized_dir_input.text(),
            "OMDB_API_KEY": self.api_key_input.text()
        }
        
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        
        reload_config()
        self.update_settings_labels()
        
        QMessageBox.information(self, "Configuration", "Configuration saved successfully!")
    def reload_stats_button(self):
        try:
            reload_stats()
            self.stats = get_stats()
            self.movies_label.setText(str(self.stats['movies']))
            self.director_label.setText(self.stats['director'])
            self.rating_label.setText(str(self.stats["rating"]))
            self.oldest_movie_label.setText(self.stats["oldest_movie"])
            self.newest_movie_label.setText(self.stats["newest_movie"])
        except Exception as e:
            print("Error loading stats:", e)
    
    def update_settings_labels(self):
        # Update Move tab
        self.move_source_label.setText(self.source_folder_input.text())
        self.move_dest_label.setText(self.all_movies_input.text())
        
        # Update Fetch tab
        self.fetch_movies_dir_label.setText(self.all_movies_input.text())
        self.fetch_json_file_label.setText(self.json_file_input.text())
        self.fetch_api_key_label.setText("*" * 8)  # Don't show actual API key
        
        # Update Categorize tab
        self.cat_movies_dir_label.setText(self.all_movies_input.text())
        self.cat_json_file_label.setText(self.json_file_input.text())
        self.cat_output_dir_label.setText(self.categorized_dir_input.text())
        
    def start_move_movies(self):
        source = Path(self.source_folder_input.text())
        destination = Path(self.all_movies_input.text())
        
        if not source.exists():
            QMessageBox.warning(self, "Error", "Source folder does not exist!")
            return
            
        if not destination.exists():
            reply = QMessageBox.question(self, "Create Folder", 
                               f"Destination folder {destination} does not exist. Create it?",
                               QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                destination.mkdir(parents=True)
            else:
                return
                
        # Clear log
        self.move_log.clear()
        
        # Create and start worker thread
        self.move_worker = WorkerThread(move_movies, source, destination)
        
        # Connect log signal to log display function
        self.move_worker.update_signal.connect(self.update_move_log)
        self.move_worker.finished_signal.connect(self.on_move_finished)
        
        # Update UI
        self.move_button.setEnabled(False)
        self.move_progress.setVisible(True)
        self.move_progress.setRange(0, 0)  # Indeterminate progress
        self.status.setText("Moving movies...")
        
        # Start worker
        self.move_worker.start()
        
    
    def update_move_log(self, text):  # Update the move log display

        self.move_log.insertHtml(text + "<br>")
        self.move_log.ensureCursorVisible()

        
    def on_move_finished(self, success):
        self.move_button.setEnabled(True)
        self.move_progress.setVisible(False)
        
        if success:
            self.status.setText("Movies moved successfully!")
            QMessageBox.information(self, "Success", "Movies have been moved successfully!")
        else:
            self.status.setText("Error moving movies!")
        
    def start_fetch_movie_info(self):
        movies_dir = Path(self.all_movies_input.text())
        json_file = Path(self.json_file_input.text())
        api_key = self.api_key_input.text()
        fetch_all = not self.fetch_missing_only.isChecked()
        
        if not movies_dir.exists():
            QMessageBox.warning(self, "Error", "Movies folder does not exist!")
            return
            
        if not api_key:
            QMessageBox.warning(self, "Error", "OMDb API key is required!")
            return
            
        # Create parent directories for JSON file if they don't exist
        json_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Clear log
        self.fetch_log.clear()
        
        # Create and start worker thread
        self.fetch_worker = WorkerThread(fetch_movie_data, movies_dir, json_file, api_key, fetch_all)
        
        # Connect log signal to log display function
        self.fetch_worker.update_signal.connect(self.update_fetch_log)
        self.fetch_worker.finished_signal.connect(self.on_fetch_finished)
        
        # Update UI
        self.fetch_button.setEnabled(False)
        self.fetch_progress.setVisible(True)
        self.fetch_progress.setRange(0, 0)  # Indeterminate progress
        self.status.setText("Fetching movie information...")
        
        # Start worker
        self.fetch_worker.start()
        
    
    def update_fetch_log(self, text):  # Update the fetch log display

        self.fetch_log.insertHtml(text + "<br>")
        self.fetch_log.ensureCursorVisible()
        
    def on_fetch_finished(self, success):
        self.fetch_button.setEnabled(True)
        self.fetch_progress.setVisible(False)
        
        if success:
            self.status.setText("Movie information fetched successfully!")
            QMessageBox.information(self, "Success", "Movie information has been fetched successfully!")
        else:
            self.status.setText("Error fetching movie information!")
        
    def start_categorize_movies(self):
        movies_dir = Path(self.all_movies_input.text())
        json_file = Path(self.json_file_input.text())
        output_dir = Path(self.categorized_dir_input.text())
        
        by_director = self.cat_by_director.isChecked()
        by_imdb = self.cat_by_imdb.isChecked()
        by_decade = self.cat_by_decade.isChecked()
        
        if not movies_dir.exists():
            QMessageBox.warning(self, "Error", "Movies folder does not exist!")
            return
            
        if not json_file.exists():
            QMessageBox.warning(self, "Error", "JSON data file does not exist! Fetch movie information first.")
            return
            
        if not by_director and not by_imdb and not by_decade:
            QMessageBox.warning(self, "Error", "Please select at least one categorization option!")
            return
            
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clear log
        self.cat_log.clear()
        
        # Create and start worker thread
        self.cat_worker = WorkerThread(create_shortcuts_and_categorize, 
                                      movies_dir, json_file, output_dir, 
                                      by_director, by_imdb, by_decade)
        
        # Connect log signal to log display function
        self.cat_worker.update_signal.connect(self.update_cat_log)
        self.cat_worker.finished_signal.connect(self.on_categorize_finished)
        
        # Update UI
        self.cat_button.setEnabled(False)
        self.cat_progress.setVisible(True)
        self.cat_progress.setRange(0, 0)  # Indeterminate progress
        self.status.setText("Categorizing movies...")
        
        # Start worker
        self.cat_worker.start()
        
    def update_cat_log(self, text):  # Update the categorize log display

        self.cat_log.insertHtml(text + "<br>")
        self.cat_log.ensureCursorVisible()
    

    def on_categorize_finished(self, success):
        self.cat_button.setEnabled(True)
        self.cat_progress.setVisible(False)
        
        if success:
            self.status.setText("Movies categorized successfully!")
            QMessageBox.information(self, "Success", "Movies have been categorized successfully!")
        else:
            self.status.setText("Error categorizing movies!")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern cross-platform style
    window = CinemaShelfGUI()
    window.setWindowIcon(QtGui.QIcon("cinema_icon.ico"))
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
