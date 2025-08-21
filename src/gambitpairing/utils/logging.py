"""Logging utilities."""

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
import sys

from PyQt6 import QtCore

# the logger format used
LOG_FMT = "LVL: %(levelname)s | FILE PATH: %(pathname)s | FUN: %(funcName)s | msg: %(message)s | ln#:%(lineno)d"


# --- Logging Setup ---
def setup_logger(logger_name: str) -> logging.Logger:
    """Set up loger for a python module.

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


#  LocalWords:  QListWidget
