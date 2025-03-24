import sys
import random
import logging
from typing import List, Optional, Tuple, Set
from PyQt6 import QtWidgets, QtGui, QtCore

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class Player:
    def __init__(self, name: str) -> None:
        """Initialize a player with a name and a starting score of 0."""
        self.name: str = name
        self.score: float = 0

    def __repr__(self) -> str:
        return self.name

class Tournament:
    def __init__(self, players: List[Player]) -> None:
        """Initialize the tournament with players and tracking variables."""
        self.players: List[Player] = players
        self.rounds: List[Tuple[List[Tuple[Player, Player]], Optional[Player]]] = []  # List of (pairings, bye)
        self.previous_matches: Set[frozenset] = set()

    def create_pairings(self) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """
        Create pairings for the round using a greedy algorithm that avoids rematches.
        Automatically awards a bye (1 point) if needed.
        """
        players_sorted = sorted(self.players, key=lambda p: (-p.score, p.name))
        unpaired = players_sorted.copy()
        pairings: List[Tuple[Player, Player]] = []
        bye: Optional[Player] = None

        while unpaired:
            p1 = unpaired.pop(0)
            opponent_found = False
            for i, p2 in enumerate(unpaired):
                key = frozenset({p1.name, p2.name})
                if key not in self.previous_matches:
                    white, black = random.choice([(p1, p2), (p2, p1)])
                    pairings.append((white, black))
                    self.previous_matches.add(key)
                    unpaired.pop(i)
                    opponent_found = True
                    logging.debug(f"Pairing: {white.name} (White) vs {black.name} (Black)")
                    break
            if not opponent_found:
                if unpaired:
                    p2 = unpaired.pop(0)
                    key = frozenset({p1.name, p2.name})
                    white, black = random.choice([(p1, p2), (p2, p1)])
                    pairings.append((white, black))
                    self.previous_matches.add(key)
                    logging.debug(f"Pairing (forced): {white.name} (White) vs {black.name} (Black)")
                else:
                    bye = p1
                    bye.score += 1  # Awarding bye point automatically
                    logging.debug(f"Bye given to: {bye.name}")
        self.rounds.append((pairings, bye))
        return pairings, bye

# Enhanced GUI using PyQt6 with improved styles
class RoundHistoryDialog(QtWidgets.QDialog):
    def __init__(self, rounds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Round History")
        layout = QtWidgets.QVBoxLayout(self)
        self.history_text = QtWidgets.QPlainTextEdit()
        self.history_text.setReadOnly(True)
        layout.addWidget(self.history_text)
        self.populate_history(rounds)
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
    
    def populate_history(self, rounds) -> None:
        """Fill the history view with past round pairings and bye information."""
        history = ""
        for index, (pairings, bye) in enumerate(rounds, 1):
            history += f"Round {index} Pairings:\n"
            for white, black in pairings:
                history += f"  {white} (White) vs {black} (Black)\n"
            if bye:
                history += f"  Bye: {bye} (1 point awarded)\n"
            history += "\n"
        self.history_text.setPlainText(history)

class SwissTournamentApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Swiss Chess Tournament")
        self.tournament: Optional[Tournament] = None
        self.round: int = 0
        self.last_round_changes = {}  # For undoing score changes

        # Overhauled GUI: Using a QTabWidget for better organization
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # ----- Tournament Tab -----
        self.tournament_tab = QtWidgets.QWidget()
        tab_layout = QtWidgets.QVBoxLayout(self.tournament_tab)
        
        # Control Panel (Player input, actions)
        control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout(control_panel)
        # Left side: Player Input & List
        player_panel = QtWidgets.QVBoxLayout()
        self.input_player_line = QtWidgets.QLineEdit()
        self.input_player_line.setPlaceholderText("Enter player name")
        self.btn_add_player = QtWidgets.QPushButton("Add Player")
        self.btn_add_player.clicked.connect(self.add_player)
        player_panel.addWidget(self.input_player_line)
        player_panel.addWidget(self.btn_add_player)
        self.list_players = QtWidgets.QListWidget()
        self.list_players.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_players.customContextMenuRequested.connect(self.on_player_context_menu)
        player_panel.addWidget(self.list_players)
        control_layout.addLayout(player_panel)
        # Right side: Tournament Actions
        action_panel = QtWidgets.QVBoxLayout()
        self.btn_start = QtWidgets.QPushButton("Start Tournament")
        self.btn_start.clicked.connect(self.start_tournament)
        action_panel.addWidget(self.btn_start)
        self.btn_next = QtWidgets.QPushButton("Next Round")
        self.btn_next.clicked.connect(self.next_round)
        self.btn_next.setEnabled(False)
        action_panel.addWidget(self.btn_next)
        self.btn_undo = QtWidgets.QPushButton("Undo Last Round")
        self.btn_undo.clicked.connect(self.undo_last_round)
        self.btn_undo.setEnabled(False)
        action_panel.addWidget(self.btn_undo)
        self.btn_history = QtWidgets.QPushButton("Round History")
        self.btn_history.clicked.connect(self.show_round_history)
        self.btn_history.setEnabled(False)
        action_panel.addWidget(self.btn_history)
        control_layout.addLayout(action_panel)
        tab_layout.addWidget(control_panel)
        
        # Results Table
        self.table_results = QtWidgets.QTableWidget(0, 4)
        self.table_results.setHorizontalHeaderLabels(["White", "Black", "White Score", "Black Score"])
        self.table_results.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        tab_layout.addWidget(self.table_results)
        
        # Bottom Panel: Pairings and Standings side by side
        bottom_panel = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.text_result = QtWidgets.QPlainTextEdit()
        self.text_result.setReadOnly(True)
        bottom_panel.addWidget(self.text_result)
        self.table_standings = QtWidgets.QTableWidget(0, 2)
        self.table_standings.setHorizontalHeaderLabels(["Player", "Score"])
        self.table_standings.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        bottom_panel.addWidget(self.table_standings)
        bottom_panel.setSizes([300,300])
        tab_layout.addWidget(bottom_panel)
        
        self.tabs.addTab(self.tournament_tab, "Tournament")
        
        # ----- History Tab -----
        self.history_tab = QtWidgets.QWidget()
        history_layout = QtWidgets.QVBoxLayout(self.history_tab)
        self.history_view = QtWidgets.QPlainTextEdit()
        self.history_view.setReadOnly(True)
        history_layout.addWidget(self.history_view)
        self.tabs.addTab(self.history_tab, "History")
        
        # Menu: Reset, Export, and Undo Last Round actions
        menu_bar = self.menuBar()
        tournament_menu = menu_bar.addMenu("Tournament")
        reset_action = QtGui.QAction("Reset Tournament", self)
        reset_action.triggered.connect(self.reset_tournament)
        tournament_menu.addAction(reset_action)
        export_action = QtGui.QAction("Export Tournament", self)
        export_action.triggered.connect(self.export_tournament)
        tournament_menu.addAction(export_action)
        undo_action = QtGui.QAction("Undo Last Round", self)
        undo_action.triggered.connect(self.undo_last_round)
        tournament_menu.addAction(undo_action)
        self.statusBar().showMessage("Ready")
    
    # New method to remove a player via context menu
    def on_player_context_menu(self, point) -> None:
        item = self.list_players.itemAt(point)
        if item:
            menu = QtWidgets.QMenu(self)
            remove_action = menu.addAction("Remove Player")
            if menu.exec(self.list_players.mapToGlobal(point)) == remove_action:
                row = self.list_players.row(item)
                self.list_players.takeItem(row)

    def add_player(self) -> None:
        name = self.input_player_line.text().strip()
        if name:
            # Optionally check if player already exists
            for index in range(self.list_players.count()):
                if self.list_players.item(index).text() == name:
                    return
            self.list_players.addItem(name)
            self.input_player_line.clear()

    def reset_tournament(self) -> None:
        reply = QtWidgets.QMessageBox.question(
            self, "Reset Tournament",
            "Are you sure you want to reset the tournament?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.tournament = None
            self.round = 0
            # Clear players list and results table; remove old widgets references not in use anymore.
            self.list_players.clear()
            self.table_results.setRowCount(0)
            self.text_result.clear()
            self.table_standings.setRowCount(0)
            self.input_player_line.setEnabled(True)
            self.btn_add_player.setEnabled(True)
            self.btn_next.setEnabled(False)
            self.btn_history.setEnabled(False)

    def start_tournament(self) -> None:
        # Use players from list widget
        names = [self.list_players.item(i).text() for i in range(self.list_players.count())]
        if len(names) < 2:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Enter at least two players.")
            return
        players = [Player(name) for name in names]
        self.tournament = Tournament(players)
        self.round = 1
        self.btn_next.setEnabled(True)
        self.btn_history.setEnabled(True)
        # Disable adding more players once the tournament starts
        self.input_player_line.setEnabled(False)
        self.btn_add_player.setEnabled(False)
        self.display_round()

    def next_round(self) -> None:
        # Check for any empty score fields
        row_count = self.table_results.rowCount()
        empty_found = any(
            not (self.table_results.item(row, 2).text().strip() and self.table_results.item(row, 3).text().strip())
            for row in range(row_count)
        )
        if empty_found:
            confirm = QtWidgets.QMessageBox.question(
                self, "Incomplete Scores",
                "Some score fields are empty. Do you want to treat empty fields as 0?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            if confirm == QtWidgets.QMessageBox.StandardButton.No:
                return

        round_changes = {}
        for row in range(row_count):
            white_item = self.table_results.item(row, 0)
            black_item = self.table_results.item(row, 1)
            white_score_item = self.table_results.item(row, 2)
            black_score_item = self.table_results.item(row, 3)
            if not white_item or not black_item:
                continue
            white_name = white_item.text()
            black_name = black_item.text()
            try:
                white_score = float(white_score_item.text()) if white_score_item and white_score_item.text() else 0
            except ValueError:
                white_score = 0
            try:
                black_score = float(black_score_item.text()) if black_score_item and black_score_item.text() else 0
            except ValueError:
                black_score = 0
            for player in self.tournament.players:
                if player.name == white_name:
                    player.score += white_score
                    round_changes[white_name] = round_changes.get(white_name, 0) + white_score
                elif player.name == black_name:
                    player.score += black_score
                    round_changes[black_name] = round_changes.get(black_name, 0) + black_score
        self.last_round_changes = round_changes
        self.btn_undo.setEnabled(True)
        self.table_results.setRowCount(0)
        self.round += 1
        self.display_round()

    def undo_last_round(self) -> None:
        """Undo the score changes from the last round."""
        if not self.last_round_changes:
            QtWidgets.QMessageBox.information(self, "Undo", "No round available to undo.")
            return
        for player in self.tournament.players:
            if player.name in self.last_round_changes:
                player.score -= self.last_round_changes[player.name]
        self.last_round_changes = {}
        self.round = max(self.round - 1, 0)
        self.update_standings()
        self.btn_undo.setEnabled(False)
        QtWidgets.QMessageBox.information(self, "Undo", "Last round has been undone.")

    def display_round(self) -> None:
        pairings, bye = self.tournament.create_pairings()
        # Update pairings text with color assignment
        output = f"Round {self.round} Pairings:\n"
        # Populate the results table with pairing info for score input
        self.table_results.setRowCount(len(pairings))
        for row, (white, black) in enumerate(pairings):
            output += f"{white} (White) vs {black} (Black)\n"
            self.table_results.setItem(row, 0, QtWidgets.QTableWidgetItem(white.name))
            self.table_results.setItem(row, 1, QtWidgets.QTableWidgetItem(black.name))
            # Leave score cells (columns 2 and 3) empty for user input
            self.table_results.setItem(row, 2, QtWidgets.QTableWidgetItem(""))
            self.table_results.setItem(row, 3, QtWidgets.QTableWidgetItem(""))
        if bye:
            output += f"\nBye: {bye} (1 point awarded)\n"
        self.text_result.setPlainText(output)
        # Update round info in status bar
        self.statusBar().showMessage(f"Round {self.round} completed")
        self.update_standings()
        # Also update the History tab
        history = ""
        for idx, (pair_list, bye) in enumerate(self.tournament.rounds, 1):
            history += f"Round {idx}:\n"
            for white, black in pair_list:
                history += f"  {white} (White) vs {black} (Black)\n"
            if bye:
                history += f"  Bye: {bye} (1 point)\n"
            history += "\n"
        self.history_view.setPlainText(history)

    def update_standings(self) -> None:
        """Helper method to update the standings table from tournament players."""
        standings = sorted(self.tournament.players, key=lambda p: (-p.score, p.name))
        self.table_standings.setRowCount(len(standings))
        for row, player in enumerate(standings):
            self.table_standings.setItem(row, 0, QtWidgets.QTableWidgetItem(player.name))
            self.table_standings.setItem(row, 1, QtWidgets.QTableWidgetItem(str(player.score)))

    def show_round_history(self) -> None:
        if self.tournament and self.tournament.rounds:
            dlg = RoundHistoryDialog(self.tournament.rounds, self)
            dlg.exec()

    def export_tournament(self) -> None:
        if not self.tournament:
            QtWidgets.QMessageBox.information(self, "Export Tournament", "No tournament data to export.")
            return
        try:
            from TournamentReporter import TournamentReporter
        except ImportError:
            QtWidgets.QMessageBox.warning(self, "Export Error", "TournamentReporter module not found!")
            return
        history = TournamentReporter(self.tournament.rounds).format_history()
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Tournament", "", "Text Files (*.txt)")
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(history)
                QtWidgets.QMessageBox.information(self, "Export Successful", f"Tournament exported to {filename}")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Export Error", f"Error saving file: {e}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = SwissTournamentApp()
    window.show()
    sys.exit(app.exec())