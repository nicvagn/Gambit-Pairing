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

    def get_opponents(self, player: Player) -> List[Player]:
        """Return a list of opponents played by the given player."""
        opponents = []
        for pairings, bye in self.rounds:
            for white, black in pairings:
                if player.name == white.name:
                    opponents.append(black)
                elif player.name == black.name:
                    opponents.append(white)
        return opponents

    def compute_tiebreakers(self) -> dict[str, dict[str, float]]:
        """Compute tiebreakers for each player.
        Returns a dict mapping player name to:
          - modified_median
          - solkoff
          - cum_score
          - cum_opp_score
        """
        tb = {}
        round_count = len(self.rounds)
        half_max = round_count / 2 if round_count > 0 else 0
        for player in self.players:
            opps = self.get_opponents(player)
            opp_scores = [opp.score for opp in opps]
            if not opp_scores:
                mod_median = 0.0
            else:
                if player.score > half_max:
                    # Plus: drop lowest opponent score
                    mod_median = sum(opp_scores) - min(opp_scores)
                elif player.score < half_max:
                    # Minus: drop highest opponent score
                    mod_median = sum(opp_scores) - max(opp_scores)
                else:
                    # Even: drop both lowest and highest if possible
                    if len(opp_scores) > 2:
                        mod_median = sum(opp_scores) - min(opp_scores) - max(opp_scores)
                    else:
                        mod_median = sum(opp_scores)
            solkoff = sum(opp_scores)
            cum_score = player.score  # Using final score as cumulative score
            cum_opp_score = sum(opp.score for opp in opps)
            tb[player.name] = {
                'modified_median': mod_median,
                'solkoff': solkoff,
                'cum_score': cum_score,
                'cum_opp_score': cum_opp_score
            }
        return tb

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
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gambit Pairing")  # Changed title from "Swiss Chess Tournament"
        self.tournament: Optional[Tournament] = None
        self.current_round: int = 1  # Renamed for clarity
        self.last_round_changes: dict[str, float] = {}

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
        # Modified: Changed button name to "View Results" instead of "End Tournament"
        view_results_action = QtGui.QAction("View Results", self)
        view_results_action.triggered.connect(self.end_tournament)
        tournament_menu.addAction(view_results_action)
        self.statusBar().showMessage("Ready")
    
    # New method to remove a player via context menu
    def on_player_context_menu(self, point: QtCore.QPoint) -> None:
        item = self.list_players.itemAt(point)
        if item:
            menu = QtWidgets.QMenu(self)
            remove_action = menu.addAction("Remove Player")
            if menu.exec(self.list_players.mapToGlobal(point)) == remove_action:
                row = self.list_players.row(item)
                self.list_players.takeItem(row)

    def add_player(self) -> None:
        """
        Add a new player into the tournament list.
        Do not allow duplicates or empty names.
        """
        name: str = self.input_player_line.text().strip()
        if not name:
            return
        for index in range(self.list_players.count()):
            if self.list_players.item(index).text() == name:
                QtWidgets.QMessageBox.warning(self, "Duplicate Player",
                                              f"Player '{name}' already exists.")
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
            self.current_round = 1
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
        self.current_round = 1
        self.btn_next.setEnabled(True)
        self.btn_history.setEnabled(True)
        # Disable adding more players once the tournament starts
        self.input_player_line.setEnabled(False)
        self.btn_add_player.setEnabled(False)
        self.display_round()

    def next_round(self) -> None:
        """
        Process the scores and advance to the next round.
        Treat empty score fields as 0 upon confirmation.
        """
        row_count = self.table_results.rowCount()
        empty_found = any(
            not (self.table_results.item(row, 2).text().strip() and
                 self.table_results.item(row, 3).text().strip())
            for row in range(row_count)
        )
        if empty_found:
            confirm = QtWidgets.QMessageBox.question(
                self, "Incomplete Scores",
                "Some score fields are empty. Treat empty fields as 0?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            if confirm == QtWidgets.QMessageBox.StandardButton.No:
                return
        
        round_changes: dict[str, float] = {}
        for row in range(row_count):
            white_name = self.table_results.item(row, 0).text()
            black_name = self.table_results.item(row, 1).text()
            try:
                white_score = float(self.table_results.item(row, 2).text().strip() or 0)
            except ValueError:
                white_score = 0.0
            try:
                black_score = float(self.table_results.item(row, 3).text().strip() or 0)
            except ValueError:
                black_score = 0.0
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
        self.current_round += 1
        self.display_round()

    def undo_last_round(self) -> None:
        """
        Revert the score changes applied in the last round.
        """
        if not self.last_round_changes:
            QtWidgets.QMessageBox.information(self, "Undo", "No round available to undo.")
            return
        for player in self.tournament.players:
            if player.name in self.last_round_changes:
                player.score -= self.last_round_changes[player.name]
        self.last_round_changes = {}
        self.current_round = max(self.current_round - 1, 1)
        self.update_standings()
        self.btn_undo.setEnabled(False)
        QtWidgets.QMessageBox.information(self, "Undo", "Last round has been undone.")
        self.update_history_view()

    def display_round(self) -> None:
        """
        Generate pairings & update UI for the current round.
        """
        pairings, bye = self.tournament.create_pairings()
        output = f"Round {self.current_round} Pairings:\n"
        self.table_results.setRowCount(len(pairings))
        for row, (white, black) in enumerate(pairings):
            output += f"{white.name} (White) vs {black.name} (Black)\n"
            self.table_results.setItem(row, 0, QtWidgets.QTableWidgetItem(white.name))
            self.table_results.setItem(row, 1, QtWidgets.QTableWidgetItem(black.name))
            self.table_results.setItem(row, 2, QtWidgets.QTableWidgetItem(""))
            self.table_results.setItem(row, 3, QtWidgets.QTableWidgetItem(""))
        if bye:
            output += f"\nBye: {bye.name} (1 point awarded)\n"
        self.text_result.setPlainText(output)
        self.statusBar().showMessage(f"Round {self.current_round} ready")
        self.update_standings()
        self.update_history_view()

    def update_history_view(self) -> None:
        """
        Consolidate tournament history and update the History tab.
        """
        history: str = ""
        for idx, (pair_list, bye) in enumerate(self.tournament.rounds, 1):
            history += f"Round {idx}:\n"
            for white, black in pair_list:
                history += f"  {white.name} (White) vs {black.name} (Black)\n"
            if bye:
                history += f"  Bye: {bye.name}\n"
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
        # Generate standings details
        standings = sorted(self.tournament.players, key=lambda p: (-p.score, p.name))
        standings_str = "Standings:\n"
        for idx, player in enumerate(standings, 1):
            standings_str += f"{idx}. {player.name} - {player.score} points\n"
        # New: Compute and append tiebreaker calculations
        tiebreakers = self.tournament.compute_tiebreakers()
        tiebreakers_str = "\nTiebreaker Calculations:\n"
        for player in standings:
            tb = tiebreakers.get(player.name, {})
            tiebreakers_str += (f"{player.name}: Modified Median = {tb.get('modified_median', 0):.1f}, "
                                f"Solkoff = {tb.get('solkoff', 0):.1f}, "
                                f"Cumulative Score = {tb.get('cum_score', 0):.1f}, "
                                f"Cumulative Opponent Score = {tb.get('cum_opp_score', 0):.1f}\n")
        export_text = standings_str + tiebreakers_str + "\n" + history
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Tournament", "", "Text Files (*.txt)")
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(export_text)
                QtWidgets.QMessageBox.information(self, "Export Successful", f"Tournament exported to {filename}")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Export Error", f"Error saving file: {e}")

    def end_tournament(self) -> None:
        """
        Display detailed tournament results without ending the tournament.
        """
        if not self.tournament:
            QtWidgets.QMessageBox.information(self, "View Results", "No tournament in progress.")
            return
        detailed: str = "Current Standings:\n"
        standings = sorted(self.tournament.players, key=lambda p: (-p.score, p.name))
        for idx, player in enumerate(standings, 1):
            detailed += f"{idx}. {player.name} - {player.score:.1f} points\n"
        detailed += "\nRound Details:\n"
        for i, (pairings, bye) in enumerate(self.tournament.rounds, 1):
            detailed += f"Round {i}:\n"
            for white, black in pairings:
                detailed += f"  {white.name} (White) vs {black.name} (Black)\n"
            if bye:
                detailed += f"  Bye: {bye.name}\n"
            detailed += "\n"
        # Append tiebreaker calculations
        tiebreakers = self.tournament.compute_tiebreakers()
        detailed += "Tiebreaker Calculations:\n"
        for player in sorted(self.tournament.players, key=lambda p: (-p.score, p.name)):
            tb = tiebreakers.get(player.name, {})
            detailed += (f"{player.name}: Modified Median = {tb.get('modified_median',0):.1f}, "
                         f"Solkoff = {tb.get('solkoff',0):.1f}, "
                         f"Cumulative Score = {tb.get('cum_score',0):.1f}, "
                         f"Cumulative Opponent Score = {tb.get('cum_opp_score',0):.1f}\n")
        detailed += "\n"
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Tournament Results")
        layout = QtWidgets.QVBoxLayout(dlg)
        text_edit = QtWidgets.QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(detailed)
        layout.addWidget(text_edit)
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close)
        dlg.exec()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = SwissTournamentApp()
    window.show()
    sys.exit(app.exec())
