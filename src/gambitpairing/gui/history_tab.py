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

from PyQt6 import QtGui, QtWidgets
from PyQt6.QtCore import QDateTime


class HistoryTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.history_view = QtWidgets.QPlainTextEdit()
        self.history_view.setReadOnly(True)
        self.history_view.setToolTip("Log of pairings, results, and actions.")
        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        self.history_view.setFont(font)
        self.main_layout.addWidget(self.history_view)

    def update_history_log(self, message: str):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.history_view.appendPlainText(f"[{timestamp}] {message}")
        logging.info(f"UI_LOG: {message}")  # Distinguish from backend logging if needed

    def update_ui_state(self):
        pass
