from PyQt6 import QtCore
import logging

class UpdateWorker(QtCore.QObject):
    """Worker thread for handling the update process in the background."""
    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(str) # Returns extracted path
    error = QtCore.pyqtSignal(str)
    done = QtCore.pyqtSignal(bool, str)  # (success, message or extracted_path)

    def __init__(self, updater):
        super().__init__()
        self.updater = updater

    def run(self):
        """Executes the update download and verification process."""
        try:
            # 1. Download
            self.status.emit("Downloading update...")
            zip_path = self.updater.download_update(self.progress.emit)
            if not zip_path:
                self.error.emit("Failed to download update.")
                self.done.emit(False, "Failed to download update.")
                return

            # 2. Verify
            self.status.emit("Verifying checksum...")
            verified = self.updater.verify_checksum(zip_path)
            if not verified:
                self.error.emit("Checksum verification failed. The file may be corrupted or tampered with.")
                self.done.emit(False, "Checksum verification failed.")
                return

            # 3. Extract
            self.status.emit("Extracting update...")
            extracted_path = self.updater.extract_update()
            if not extracted_path:
                self.error.emit("Failed to extract update file.")
                self.done.emit(False, "Failed to extract update file.")
                return
            self.status.emit("Update ready to install.")
            self.finished.emit(extracted_path)
            self.done.emit(True, extracted_path)
        except Exception as e:
            logging.error(f"Error in update worker: {e}", exc_info=True)
            self.error.emit(f"An unexpected error occurred: {e}")
            self.done.emit(False, f"An unexpected error occurred: {e}")
