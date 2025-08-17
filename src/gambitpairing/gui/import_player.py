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
from gambitpairing.gui.mainwindow import GambitPairingMainWindow

logger = setup_logger(__name__)


class ImportPlayers:
    def import_players_from_fide(cls, main_window: GambitPairingMainWindow):
        if not main_window.tournament:
            QtWidgets.QMessageBox.warning(
                main_window,
                "No Tournament",
                "Please create a tournament before importing players.",
            )
            return
        if len(main_window.tournament.rounds_pairings_ids) > 0:
            QtWidgets.QMessageBox.warning(
                main_window,
                "Tournament Active",
                "Cannot import players after the tournament has started.",
            )
            return

        dialog = PlayerManagementDialog(
            parent=main_window, tournament=main_window.tournament
        )
        dialog.tab_widget.setCurrentIndex(1)  # Switch to FIDE tab
        if dialog.exec():
            # Player was added through the integrated dialog
            main_window.players_tab.refresh_player_list()
            main_window.players_tab.update_ui_state()
            main_window.mark_dirty()

    def import_players_from_cfc(cls, main_window: GambitPairingMainWindow):
        if not main_window.tournament:
            QtWidgets.QMessageBox.warning(
                main_window,
                "No Tournament",
                "Please create a tournament before importing players.",
            )
            return
        if len(main_window.tournament.rounds_pairings_ids) > 0:
            QtWidgets.QMessageBox.warning(
                main_window,
                "Tournament Active",
                "Cannot import players after the tournament has started.",
            )
            return

        # Open PlayerManagementDialog on FIDE tab
        from .dialogs import PlayerManagementDialog

        dialog = PlayerManagementDialog(
            parent=main_window, tournament=main_window.tournament
        )
        dialog.tab_widget.setCurrentIndex(1)  # Switch to FIDE tab
        if dialog.exec():
            # Player was added through the integrated dialog
            main_window.players_tab.refresh_player_list()
            main_window.players_tab.update_ui_state()
            main_window.mark_dirty()

    def import_players_from_ufc(ImportPlayers):
        raise NotImplementedError("Not done. You should do it")
