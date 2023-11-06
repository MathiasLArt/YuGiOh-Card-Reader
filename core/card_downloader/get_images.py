import sys
import json
import os
import requests
import re
import time
import argparse
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QCheckBox, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, QProgressBar
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QIcon

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

class CardImageDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.worker = None

    def init_ui(self):
        self.setWindowTitle("YGO Image Downloader")
        self.setFixedSize(400, 100)  # Set a fixed size
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        icon = QIcon("core\\card_downloader\\icon.png")  # Replace with the actual path to your icon image
        self.setWindowIcon(icon)

        self.layout = QVBoxLayout()

        # Create a progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)  # Initialize the progress bar
        self.layout.addWidget(self.progress_bar)

        # Create a horizontal layout for the bottom part
        bottom_layout = QHBoxLayout()

        self.start_button = QPushButton("Start Download", self)
        self.start_button.clicked.connect(self.start_download)
        bottom_layout.addWidget(self.start_button)

        self.force_checkbox = QCheckBox("Force Download", self)
        bottom_layout.addWidget(self.force_checkbox)

        # Add the horizontal layout for the bottom part to the main vertical layout
        self.layout.addLayout(bottom_layout)

        self.central_widget.setLayout(self.layout)

    def start_download(self):
        if self.worker is None or not self.worker.isRunning():
            force = self.force_checkbox.isChecked()
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

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        self.update_title(value, self.progress_bar.maximum())  # Update the title based on the progress

    def update_title(self, current, total):
        new_title = f"YGO Image Downloader ({current} / {total})"
        self.setWindowTitle(new_title)  # Set the window title directly


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