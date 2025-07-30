import logging
import os
import random
import subprocess
import sys
import time

from PyQt6 import QtCore
from PyQt6.QtCore import QDateTime
from PyQt6.QtWidgets import QApplication, QStyleFactory

# --- Logging Setup ---
# Setup logging to file and console
log_formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s")
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)  # Set minimum level

# File Handler
try:
    # Attempt to create a log file in the user's home directory or a temp directory
    log_dir = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.StandardLocation.AppDataLocation
    )
    if not log_dir:
        log_dir = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.StandardLocation.TempLocation
        )
    if log_dir:
        log_path = QtCore.QDir(log_dir).filePath("gambit_pairing.log")
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)
        print(f"Logging to: {log_path}")  # Inform user where logs are
    else:
        print("Warning: Could not determine writable location for log file.")
except Exception as e:
    print(f"Warning: Could not create log file handler: {e}")


# Console Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)


# --- GUI Restart Functionality ---
def restart_application():
    """Restart the entire application to ensure clean state reload."""

    # Get the current application instance
    app = QApplication.instance()
    if app is None:
        return False

    # Get command line arguments for restart
    args = sys.argv[:]

    # Close all windows and quit the application
    app.closeAllWindows()
    app.quit()

    # Small delay to ensure cleanup
    time.sleep(0.1)

    # Restart the application
    try:
        if sys.platform == "win32":
            subprocess.Popen([sys.executable] + args)
        else:
            # For Linux/Unix systems, use os.execv for cleaner restart
            os.execv(sys.executable, [sys.executable] + args)
        return True
    except Exception as e:
        root_logger.error(f"Failed to restart application: {e}")
        return False


# --- Style Management ---
class StyleManager:
    """Centralized style management for legacy GUI support."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.legacy_mode = False
            self._initialized = True

    def apply_style(self, widget, style_sheet: str):
        """Apply a stylesheet to a widget and track it for legacy mode."""
        try:
            widget.setStyleSheet(style_sheet)
        except RuntimeError:
            # Widget may have been deleted, ignore
            pass
        # Set WindowsVista style for legacy mode
        app = QApplication.instance()
        if app is not None:
            try:
                available_styles = QStyleFactory.keys()
                if "Fusion" in available_styles:
                    app.setStyle("WindowsVista")
            except Exception:
                pass


# Global style manager instance
style_manager = StyleManager()


def apply_stylesheet(widget, style_sheet: str):
    """Apply a stylesheet with legacy GUI support."""
    style_manager.apply_style(widget, style_sheet)


# --- Utility Functions ---
def generate_id(prefix: str = "item_") -> str:
    """Generates a simple unique ID."""
    return f"{prefix}{random.randint(100000, 999999)}_{int(QDateTime.currentMSecsSinceEpoch())}"
