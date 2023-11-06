import sys
import json
import os
import requests
import re
import time
import argparse
from PyQt6.QtWidgets import QApplication,QFormLayout,QLineEdit, QDialog, QMainWindow, QPushButton, QCheckBox, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, QProgressBar
from PyQt6.QtCore import QThread, Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor, QPalette

# Get the directory of the current script
current_script_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.abspath(os.path.join(current_script_dir, os.pardir))
sys.path.append(parent_dir)

from logger import setup_logger

class DownloadWorker(QThread):
    update_progress = pyqtSignal(int)  # Signal to update the progress
    download_finished = pyqtSignal()

    def __init__(self, data, card_dir, force):
        super().__init__()
        self.data = data
        self.card_dir = card_dir
        self.force = force

    def run(self):
        for key, card in enumerate(self.data):
            if self.isInterruptionRequested():
                break  # Exit the loop if the thread is interrupted
            self.download_image(card, self.card_dir, force=self.force)
            self.update_progress.emit(key + 1)  # Update progress
        self.download_finished.emit()

    def download_image(self, card, output_dir, force=False):
        if 'image_url' in card['card_images'][0]:
            card_id = card['id']
            url = card['card_images'][0]['image_url']
            extension = url.split('.')[-1]

            image_path = os.path.join(output_dir, f'{card_id}.{extension}')

            if not force:
                # Check if the file already exists and skip if it does
                if os.path.exists(image_path):
                    logger.info(f"Image for {card['name']} already exists, skipping download.")
                    return

            try:
                response = requests.get(url, headers={'User-Agent': 'Your User Agent'})
                response.raise_for_status()  # Check for HTTP status code errors

                if response.status_code == 200:
                    with open(image_path, 'wb') as img_file:
                        img_file.write(response.content)
                    logger.info(f"Downloaded image {card['id']} ({card['name']})")
                else:
                    logger.warning(f"Failed to download image for {card['name']} (HTTP status code: {response.status_code})")
            except Exception as e:
                logger.error(f"Error downloading image for {card['name']}: {str(e)}")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        layout = QVBoxLayout()
        settings_layout = QFormLayout()

        # declare settings
        self.force_checkbox = QCheckBox("Force Download", self)
        settings_layout.addRow(self.force_checkbox)

        self.card_dir_edit = QLineEdit(self)
        self.card_dir_edit.setPlaceholderText("Card Directory")
        settings_layout.addRow("Card Directory", self.card_dir_edit)

        #setting defaults
        #TODO write settings to .ini file upon clicking apply. 
        #TODO read settings from .ini when user clicked revert (returning to previous )

        self.original_force_download = self.force_checkbox.isChecked()
        self.original_card_dir = self.card_dir_edit.text()

        # Apply alternating background colors to form layout rows
        for i in range(settings_layout.rowCount()):
            widget = settings_layout.itemAt(i).widget()
            if i % 2 == 0:
                widget.setStyleSheet("background-color: #F0F0F0;")
            else:
                widget.setStyleSheet("background-color: #DCDCDC;")

        #Add apply and default button 
        bottom_layout = QHBoxLayout()
        apply_button = QPushButton("Apply", self)
        apply_button.clicked.connect(self.accept)
        bottom_layout.addWidget(apply_button)

        default_button = QPushButton("Defaults", self)
        default_button.clicked.connect(self.default_settings)
        bottom_layout.addWidget(default_button)


        layout.addLayout(settings_layout)
        layout.addLayout(bottom_layout)


        self.setLayout(layout)
        self.setFixedSize(400, self.calculate_height())


    def calculate_height(self):
        # Calculate the height based on the number of rows in the form layout
        settings_layout = self.layout().itemAt(0).layout()
        row_height = 25  # Height of each row
        num_rows = settings_layout.rowCount()
        extra_space = 60  # Additional space for buttons and padding
        return num_rows * row_height + extra_space

    #GET / SET --force setting
    def get_force_download(self):
        # Get the state of the "Force Download" checkbox
        return self.force_checkbox.isChecked()

    def set_force_download(self, checked):
        # Set the state of the "Force Download" checkbox
        self.force_checkbox.setChecked(checked)

    def get_card_dir(self):
        # Get the value of the card directory setting
        return self.card_dir_edit.text()

    def set_card_dir(self, card_dir):
        # Set the value of the card directory setting
        self.card_dir_edit.setText(card_dir)

    def default_settings(self):
            # default the settings to their original values
            self.set_force_download(self.original_force_download)

class CardImageDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.worker = None
        self._force_download = False

    def init_ui(self):
        self.setWindowTitle("YGO Image Downloader")
        self.setFixedSize(400, 100)  # Set a fixed size
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        icon = QIcon("core\\card_downloader\\icons\\icon.png")  # Replace with the actual path to your icon image
        self.setWindowIcon(icon)

        self.layout = QVBoxLayout()

        # Create a progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)  # Initialize the progress bar
        self.layout.addWidget(self.progress_bar)

        # Create a horizontal layout for the bottom part
        bottom_layout = QHBoxLayout()

        #start download button
        self.start_button = QPushButton("Download", self)
        self.start_button.setIcon(QIcon("core\\card_downloader\\icons\\downloads.png"))  # Replace with the path to your icon
        self.start_button.setToolTip("Click to start downloading card images")
        self.start_button.clicked.connect(self.start_download)
        bottom_layout.addWidget(self.start_button)

        #settings button
        self.settings_button = QPushButton(self)
        settings_icon = QIcon("core\card_downloader\icons\settings.png")  # Replace with the path to your settings icon

        self.settings_button.setIcon(QIcon(settings_icon))  # Replace with the path to your settings icon
        self.settings_button.setToolTip("Click to open the settings window")
        self.settings_button.setIconSize(QSize(settings_icon.actualSize(QSize(20, 20))))  # Set the size based on the icon
        self.settings_button.setFixedSize(self.settings_button.iconSize())  # Set the button size to match the icon
        self.settings_button.setStyleSheet("border: none; outline: none;")
       
        self.settings_button.clicked.connect(self.open_settings)
        bottom_layout.addWidget(self.settings_button)

        # Add the horizontal layout for the bottom part to the main vertical layout
        self.layout.addLayout(bottom_layout)

        self.central_widget.setLayout(self.layout)

    def start_download(self):
        if self.worker is None or not self.worker.isRunning():
            force = self.force_download
            json_file = 'core\\cardinfo.php'
            if not os.path.exists(json_file):
                QMessageBox.critical(None, "Error", f"File '{json_file}' not found in the current directory.")
                return

            with open(json_file, 'r') as file:
                data = json.load(file)['data']

            num_entries = len(data)  # Calculate the number of entries

            self.progress_bar.setValue(0)  # Reset the progress bar to the initial value
            self.progress_bar.setMaximum(num_entries)  # Set the maximum value to the number of entries

            card_dir = 'core\\card_downloader\\cards'
            os.makedirs(card_dir, exist_ok=True)

            self.worker = DownloadWorker(data, card_dir, force)
            self.worker.update_progress.connect(self.update_progress)
            self.worker.download_finished.connect(self.download_finished)
            self.worker.start()
   
    @property
    def force_download(self):
        return self._force_download

    @force_download.setter
    def force_download(self, value):
        self._force_download = value
        
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        self.update_title(value, self.progress_bar.maximum())  # Update the title based on the progress

    def update_title(self, current, total):
        new_title = f"YGO Image Downloader ({current} / {total})"
        self.setWindowTitle(new_title)  # Set the window title directly

    def open_settings(self):
        settings_dialog = SettingsDialog(self)
        # Retrieve the current state of the "Force Download" checkbox
        force_download_state = self.force_download  # Use the property to get the state
        settings_dialog.set_force_download(force_download_state)

        result = settings_dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            # Retrieve the updated state of the "Force Download" checkbox
            force_download_state = settings_dialog.get_force_download()
            # Apply the updated state using the property
            self.force_download = force_download_state


    def download_finished(self):
        self.worker = None
        QMessageBox.information(None, "Download Complete", "Download finished.")
 

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='Skip the check for existing files')
    args = parser.parse_args()

    logger = setup_logger()

    app = QApplication(sys.argv)
    downloader_app = CardImageDownloaderApp()
    downloader_app.show()
    sys.exit(app.exec())