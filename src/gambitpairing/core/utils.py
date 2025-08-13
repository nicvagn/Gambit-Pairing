# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
import os
import random
import subprocess
import sys
import time

from PyQt6 import QtCore
from PyQt6.QtCore import QDateTime
from PyQt6.QtWidgets import QApplication

# the logger format used
LOG_FMT = "%(asctime)s |:| LEVEL: %(levelname)s |:| FILE PATH: %(pathname)s |:| FUNCTION/METHOD: %(funcName)s %(message)s |:| LINE NO.: %(lineno)d |:| PROCESS ID: %(process)d |:| THREAD ID: %(thread)d"


# --- Logging Setup ---
def setup_logger(logger_name: str) -> logging.Logger:
    """Set up loger for a python module

    Sets up file handler and console handler

    Parameters
    ----------
    logger_name : str
        The name for the logger, __name__ is idiomatic

    Returns
    -------
    logging.Logger
        the created logger
    """
    # Setup logging to file and console
    lgr = logging.getLogger(name=logger_name)
    lgr.setLevel(logging.INFO)  # Set minimum level
    # formatter
    log_formatter = logging.Formatter(LOG_FMT)
    # File Handler
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
        print(f"Logging to: {log_path}")  # Inform user where logs are
    else:
        print("Warning: Could not determine writable location for log file.")
        file_handler = False

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    lgr.addHandler(console_handler)
    # add handlers
    if file_handler:
        lgr.addHandler(file_handler)
    lgr.addHandler(console_handler)
    lgr.debug("logger %s initialized", logger_name)
    return lgr


# --- GUI Restart Functionality ---
def restart_application() -> None:
    """Restart the entire application to ensure clean state reload.

    Raises
    ------
    an exception if one is raised when trying to restart
    """

    # Get the current application instance
    app = QApplication.instance()
    if app is None:
        logging.error("app is None in restart_application")
        return

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
        log = setup_logger(__name__)
        log.error(f"Failed to restart application: {e}")
        raise e


# --- Utility Functions ---
def generate_id(prefix: str = "item_") -> str:
    """Generates a simple unique ID."""
    return f"{prefix}{random.randint(100000, 999999)}_{int(QDateTime.currentMSecsSinceEpoch())}"
