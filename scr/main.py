import sys
import random
import logging
from PyQt6 import QtWidgets, QtGui, QtCore

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class Player:
    def __init__(self, name):
        self.name = name
        self.score = 0
    def __repr__(self):
        return self.name

class Tournament:
    def __init__(self, players):
        self.players = players
        self.rounds = []  # Track each round's results
        self.previous_matches = set()  # Track previous pairings (as frozensets)
    
    def create_pairings(self):
        # Improved pairing algorithm with color assignment: Greedy matching avoiding rematches if possible.
        players_sorted = sorted(self.players, key=lambda p: (-p.score, p.name))
        unpaired = players_sorted.copy()
        pairings = []
        bye = None
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
                    bye.score += 1  # award bye point
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
    
    def populate_history(self, rounds):
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
        self.tournament = None
        self.round = 0

        # Central widget and QSplitter layout for better separation
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.addWidget(splitter)

        # Top panel: Inputs
        input_widget = QtWidgets.QWidget()
        input_layout = QtWidgets.QVBoxLayout(input_widget)
        # Remove players QPlainTextEdit and add a new players input system
        self.player_entry_layout = QtWidgets.QHBoxLayout()
        self.input_player_line = QtWidgets.QLineEdit()
        self.input_player_line.setPlaceholderText("Enter player name")
        self.btn_add_player = QtWidgets.QPushButton("Add Player")
        self.btn_add_player.clicked.connect(self.add_player)
        self.player_entry_layout.addWidget(self.input_player_line)
        self.player_entry_layout.addWidget(self.btn_add_player)
        input_layout.addLayout(self.player_entry_layout)
        self.list_players = QtWidgets.QListWidget()
        # Added context-menu support for removing players
        self.list_players.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_players.customContextMenuRequested.connect(self.on_player_context_menu)
        input_layout.addWidget(self.list_players)

        self.btn_start = QtWidgets.QPushButton("Start Tournament")
        self.btn_start.clicked.connect(self.start_tournament)
        input_layout.addWidget(self.btn_start)

        # Replace freeform results input with a results table for current pairings
        self.table_results = QtWidgets.QTableWidget(0, 4)
        self.table_results.setHorizontalHeaderLabels(["White", "Black", "White Score", "Black Score"])
        self.table_results.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        input_layout.addWidget(self.table_results)

        self.btn_next = QtWidgets.QPushButton("Next Round")
        self.btn_next.clicked.connect(self.next_round)
        self.btn_next.setEnabled(False)
        input_layout.addWidget(self.btn_next)

        self.btn_history = QtWidgets.QPushButton("Round History")
        self.btn_history.clicked.connect(self.show_round_history)
        self.btn_history.setEnabled(False)
        input_layout.addWidget(self.btn_history)

        splitter.addWidget(input_widget)

        # Bottom panel: Outputs
        output_widget = QtWidgets.QWidget()
        output_layout = QtWidgets.QVBoxLayout(output_widget)
        self.pairings_label = QtWidgets.QLabel("Round Pairings:")
        output_layout.addWidget(self.pairings_label)
        self.text_result = QtWidgets.QPlainTextEdit()
        self.text_result.setReadOnly(True)
        output_layout.addWidget(self.text_result)

        self.standings_label = QtWidgets.QLabel("Standings:")
        output_layout.addWidget(self.standings_label)
        self.table_standings = QtWidgets.QTableWidget(0, 2)
        self.table_standings.setHorizontalHeaderLabels(["Player", "Score"])
        self.table_standings.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        output_layout.addWidget(self.table_standings)

        splitter.addWidget(output_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        # Menu with Reset and Export options
        menu_bar = self.menuBar()
        tournament_menu = menu_bar.addMenu("Tournament")
        reset_action = QtGui.QAction("Reset Tournament", self)
        reset_action.triggered.connect(self.reset_tournament)
        tournament_menu.addAction(reset_action)
        export_action = QtGui.QAction("Export Tournament", self)
        export_action.triggered.connect(self.export_tournament)
        tournament_menu.addAction(export_action)

        # Apply enhanced high-contrast style sheet and custom fonts for better visibility
        self.setStyleSheet("""
            QMainWindow { 
                background-color: #2e2e2e; 
                font-family: Arial, sans-serif; 
                font-size: 14px; 
                color: #f0f0f0; 
            }
            QPushButton { 
                background-color: #444444; 
                border: none; 
                padding: 8px; 
                font-size: 14px; 
                color: #f0f0f0; 
            }
            QPushButton:hover { 
                background-color: #555555; 
            }
            QPlainTextEdit, QTableWidget { 
                background-color: #3e3e3e; 
                color: #f0f0f0; 
                border: 1px solid #555555; 
            }
            QLabel { 
                color: #f0f0f0; 
            }
            QHeaderView::section { 
                background-color: #444444; 
                color: #f0f0f0; 
                padding: 4px; 
            }
        """)
        # Set global font for readability
        app_font = QtGui.QFont("Arial", 12)
        self.setFont(app_font)
        self.statusBar().showMessage("Ready")

    # New method to remove a player via context menu
    def on_player_context_menu(self, point):
        item = self.list_players.itemAt(point)
        if item:
            menu = QtWidgets.QMenu(self)
            remove_action = menu.addAction("Remove Player")
            if menu.exec(self.list_players.mapToGlobal(point)) == remove_action:
                row = self.list_players.row(item)
                self.list_players.takeItem(row)

    def add_player(self):
        name = self.input_player_line.text().strip()
        if name:
            # Optionally check if player already exists
            for index in range(self.list_players.count()):
                if self.list_players.item(index).text() == name:
                    return
            self.list_players.addItem(name)
            self.input_player_line.clear()

    def reset_tournament(self):
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

    def start_tournament(self):
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

    def next_round(self):
        # Check for any empty score fields
        row_count = self.table_results.rowCount()
        empty_found = False
        for row in range(row_count):
            white_score_item = self.table_results.item(row, 2)
            black_score_item = self.table_results.item(row, 3)
            if (not white_score_item or white_score_item.text().strip() == "") or \
               (not black_score_item or black_score_item.text().strip() == ""):
                empty_found = True
                break
        if empty_found:
            confirm = QtWidgets.QMessageBox.question(
                self, "Incomplete Scores",
                "Some score fields are empty. Do you want to treat empty fields as 0?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            if confirm == QtWidgets.QMessageBox.StandardButton.No:
                return

        # Iterate through results table to update scores
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
                elif player.name == black_name:
                    player.score += black_score
        self.table_results.setRowCount(0)
        self.round += 1
        self.display_round()

    def display_round(self):
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
        # Update standings table
        standings = sorted(self.tournament.players, key=lambda p: (-p.score, p.name))
        self.table_standings.setRowCount(len(standings))
        for row, player in enumerate(standings):
            self.table_standings.setItem(row, 0, QtWidgets.QTableWidgetItem(player.name))
            self.table_standings.setItem(row, 1, QtWidgets.QTableWidgetItem(str(player.score)))

    def show_round_history(self):
        if self.tournament and self.tournament.rounds:
            dlg = RoundHistoryDialog(self.tournament.rounds, self)
            dlg.exec()

    def export_tournament(self):
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