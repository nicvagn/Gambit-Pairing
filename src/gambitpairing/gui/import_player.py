from typing import List, Optional, Tuple

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QFileInfo, Qt
from PyQt6.QtGui import QAction, QCloseEvent
from PyQt6.QtWidgets import QMessageBox

from gambitpairing import APP_NAME, APP_VERSION
from gambitpairing.core import utils
from gambitpairing.core.tournament import Tournament
from gambitpairing.core.utils import setup_logger
from gambitpairing.gui.dialogs import (
    PlayerManagementDialog,
)

logger = setup_logger(__name__)


class ImportPlayer:
    def __init__(self, main_window) -> None:
        """Initilize an import players class. Is utilized to import players"""
        logger.info("%s initialized with main_window: %s", self, main_window)
        self.main_window = main_window

    def import_players_from_fide(self) -> None:
        breakpoint()
        if not self.main_window.tournament:
            QtWidgets.QMessageBox.warning(
                self.main_window,
                "No Tournament",
                "Please create a tournament before importing players.",
            )
            return
        if len(self.main_window.tournament.rounds_pairings_ids) > 0:
            QtWidgets.QMessageBox.warning(
                self.main_window,
                "Tournament Active",
                "Cannot import players after the tournament has started.",
            )
            return

        dialog = PlayerManagementDialog(
            parent=self.main_window, tournament=self.main_window.tournament
        )
        dialog.tab_widget.setCurrentIndex(1)  # Switch to FIDE tab
        if dialog.exec():
            # Player was added through the integrated dialog
            self.main_window.players_tab.refresh_player_list()
            self.main_window.players_tab.update_ui_state()
            self.main_window.mark_dirty()

    def import_players_from_cfc(self) -> None:
        if not self.main_window.tournament:
            QtWidgets.QMessageBox.warning(
                self.main_window,
                "No Tournament",
                "Please create a tournament before importing players.",
            )
            return
        if len(self.main_window.tournament.rounds_pairings_ids) > 0:
            QtWidgets.QMessageBox.warning(
                self.main_window,
                "Tournament Active",
                "Cannot import players after the tournament has started.",
            )
            return

        dialog = PlayerManagementDialog(
            parent=self.main_window, tournament=self.main_window.tournament
        )
        dialog.tab_widget.setCurrentIndex(1)  # Switch to FIDE tab
        if dialog.exec():
            # Player was added through the integrated dialog
            self.main_window.players_tab.refresh_player_list()
            self.main_window.players_tab.update_ui_state()
            self.main_window.mark_dirty()

    def import_players_from_uscf(self, ImportPlayers):
        raise NotImplementedError("Not done. You should do it")


#  LocalWords:  GambitPairingMainWindow
