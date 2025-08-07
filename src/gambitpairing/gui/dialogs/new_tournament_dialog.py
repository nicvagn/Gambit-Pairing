from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import Qt
from typing import List, Optional, Tuple
from gambitpairing.core.constants import TIEBREAK_NAMES, DEFAULT_TIEBREAK_SORT_ORDER


class NewTournamentDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Tournament")
        self.setMinimumWidth(350)
        self.current_tiebreak_order = list(DEFAULT_TIEBREAK_SORT_ORDER)

        self.layout = QtWidgets.QVBoxLayout(self)

        # General Settings
        general_group = QtWidgets.QGroupBox("General")
        form_layout = QtWidgets.QFormLayout(general_group)
        self.name_edit = QtWidgets.QLineEdit("My Swiss Tournament")
        self.rounds_spin = QtWidgets.QSpinBox()
        self.rounds_spin.setRange(1, 50)
        self.rounds_spin.setValue(5)
        form_layout.addRow("Tournament Name:", self.name_edit)
        form_layout.addRow("Number of Rounds:", self.rounds_spin)
        self.layout.addWidget(general_group)

        # Tiebreak Order Settings
        tiebreak_group = QtWidgets.QGroupBox("Tiebreak Order")
        tiebreak_layout = QtWidgets.QHBoxLayout(tiebreak_group)
        self.tiebreak_list = QtWidgets.QListWidget()
        self.tiebreak_list.setToolTip(
            "Order in which tiebreaks are applied (higher is better). Drag to reorder."
        )
        self.tiebreak_list.setDragDropMode(
            QtWidgets.QAbstractItemView.DragDropMode.InternalMove
        )
        self.populate_tiebreak_list()
        tiebreak_layout.addWidget(self.tiebreak_list)

        move_button_layout = QtWidgets.QVBoxLayout()
        btn_up = QtWidgets.QPushButton("Up")
        btn_down = QtWidgets.QPushButton("Down")
        btn_up.clicked.connect(self.move_tiebreak_up)
        btn_down.clicked.connect(self.move_tiebreak_down)
        move_button_layout.addStretch()
        move_button_layout.addWidget(btn_up)
        move_button_layout.addWidget(btn_down)
        move_button_layout.addStretch()
        tiebreak_layout.addLayout(move_button_layout)
        self.layout.addWidget(tiebreak_group)

        # Pairing System Selection
        pairing_group = QtWidgets.QGroupBox("Pairing System")
        pairing_layout = QtWidgets.QHBoxLayout(pairing_group)
        self.pairing_combo = QtWidgets.QComboBox()
        self.pairing_combo.addItem("Dutch System (FIDE/USCF-style)", "dutch_swiss")
        self.pairing_combo.addItem("Round Robin (All-Play-All)", "round_robin")
        self.pairing_combo.addItem("Manual Pairing", "manual")
        self.pairing_combo.setToolTip("Select the pairing system for this tournament.")
        pairing_layout.addWidget(self.pairing_combo)
        info_btn = QtWidgets.QPushButton("About Pairing Systems")
        info_btn.clicked.connect(self.show_pairing_info)
        pairing_layout.addWidget(info_btn)
        self.layout.addWidget(pairing_group)

        # Dialog Buttons
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum
        )
        self.buttons.setMinimumHeight(40)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

        # Pairing system change handling
        self.pairing_combo.currentIndexChanged.connect(self.on_pairing_system_changed)
        # Track player count for round robin (default: 5)
        self.player_count = 5
        self.rounds_spin.valueChanged.connect(self.on_rounds_changed)
        self.on_pairing_system_changed()  # Set initial state

    def populate_tiebreak_list(self):
        self.tiebreak_list.clear()
        for tb_key in self.current_tiebreak_order:
            display_name = TIEBREAK_NAMES.get(tb_key, tb_key)
            item = QtWidgets.QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, tb_key)
            self.tiebreak_list.addItem(item)

    def move_tiebreak_up(self):
        current_row = self.tiebreak_list.currentRow()
        if current_row > 0:
            item = self.tiebreak_list.takeItem(current_row)
            self.tiebreak_list.insertItem(current_row - 1, item)
            self.tiebreak_list.setCurrentRow(current_row - 1)

    def move_tiebreak_down(self):
        current_row = self.tiebreak_list.currentRow()
        if current_row < self.tiebreak_list.count() - 1:
            item = self.tiebreak_list.takeItem(current_row)
            self.tiebreak_list.insertItem(current_row + 1, item)
            self.tiebreak_list.setCurrentRow(current_row + 1)

    def update_order_from_list(self):
        self.current_tiebreak_order = [
            self.tiebreak_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.tiebreak_list.count())
        ]

    def accept(self):
        self.update_order_from_list()
        super().accept()

    def show_pairing_info(self):
        info = {
            "dutch_swiss": {
                "title": "Dutch System",
                "desc": "The most widely used Swiss system: players are grouped by score, then paired top-half vs bottom-half within each group, avoiding repeats and balancing colors. Used in FIDE and USCF events. <b>Note:</b> This system is still being developed in Gambit Pairing.",
                "fide": True,
                "uscf": True,
                "details": "<ul><li><b>Pairing Logic:</b> Players are sorted by score, then paired top vs bottom within each score group, avoiding previous opponents and balancing colors.</li><li><b>Best For:</b> Most open tournaments, FIDE/USCF events.</li><li><b>Notes:</b> This is the standard Swiss system for rated events. <b>Note:</b> This system is still being developed in Gambit Pairing.</li></ul>",
            },
            "round_robin": {
                "title": "Round Robin",
                "desc": "Every player plays every other player. Used for small events and FIDE title norm tournaments.",
                "fide": True,
                "uscf": True,
                "details": "<ul><li><b>Pairing Logic:</b> All-play-all, each player faces every other once.</li><li><b>Best For:</b> Small groups, title norm events, club championships.</li><li><b>Notes:</b> Number of rounds = number of players - 1.</li></ul>",
            },
            "manual": {
                "title": "Manual Pairing",
                "desc": "Complete manual control over all pairings. Tournament director creates all pairings by hand for each round.",
                "fide": False,
                "uscf": False,
                "details": "<ul><li><b>Pairing Logic:</b> No automatic pairing. TD manually creates all matches each round.</li><li><b>Best For:</b> Special events, demonstration games, custom formats.</li><li><b>Features:</b> Full pairing editor with drag-and-drop, player pool, edit mode for swapping players.</li><li><b>Notes:</b> Maximum flexibility but requires manual work for every round.</li></ul>",
            },
        }
        # Modern dialog with sidebar
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("About Pairing Systems")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(350)
        layout = QtWidgets.QHBoxLayout(dialog)
        # Sidebar (Table of Contents)
        toc = QtWidgets.QListWidget()
        toc.setMaximumWidth(200)
        toc.setStyleSheet("font-size: 11pt;")
        toc.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        keys = list(info.keys())
        for k in keys:
            item = QtWidgets.QListWidgetItem(info[k]["title"])
            item.setData(Qt.ItemDataRole.UserRole, k)
            toc.addItem(item)
        layout.addWidget(toc)
        # Details pane
        details_widget = QtWidgets.QWidget()
        details_layout = QtWidgets.QVBoxLayout(details_widget)
        title_label = QtWidgets.QLabel()
        title_label.setStyleSheet("font-size: 15pt; font-weight: bold; margin-bottom: 6px;")
        desc_label = QtWidgets.QLabel()
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 11pt; margin-bottom: 8px;")
        html_details = QtWidgets.QTextBrowser()
        html_details.setOpenExternalLinks(True)
        html_details.setStyleSheet(
            "background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px; font-size: 10.5pt;"
        )
        details_layout.addWidget(title_label)
        details_layout.addWidget(desc_label)
        details_layout.addWidget(html_details)
        details_layout.addStretch()
        layout.addWidget(details_widget)

        def update_details(idx):
            key = toc.item(idx).data(Qt.ItemDataRole.UserRole)
            d = info.get(key, {})
            title_label.setText(d.get("title", ""))
            desc_label.setText(d.get("desc", ""))
            html_details.setHtml(d.get("details", ""))

        toc.currentRowChanged.connect(update_details)
        # Select the current pairing system by default
        current_key = self.pairing_combo.currentData()
        default_idx = keys.index(current_key) if current_key in keys else 0
        toc.setCurrentRow(default_idx)
        update_details(default_idx)
        dialog.exec()

    def get_data(self) -> Optional[Tuple[str, int, List[str], str]]:
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(
                self, "Input Error", "Tournament name cannot be empty."
            )
            return None
        pairing_system = self.pairing_combo.currentData()
        return (
            name,
            self.rounds_spin.value(),
            self.current_tiebreak_order,
            pairing_system,
        )

    def on_pairing_system_changed(self):
        key = self.pairing_combo.currentData()
        if key == "round_robin":
            # For round robin, rounds = players - 1, hide the input
            self.rounds_spin.hide()
            label = (
                self.layout.itemAt(0).widget().layout().labelForField(self.rounds_spin)
            )
            if label:
                label.hide()
            self.rounds_spin.setToolTip(
                "Number of rounds is fixed for Round Robin: players - 1."
            )
            self.rounds_spin.setValue(max(1, self.player_count - 1))
        else:
            self.rounds_spin.show()
            label = (
                self.layout.itemAt(0).widget().layout().labelForField(self.rounds_spin)
            )
            if label:
                label.show()
            self.rounds_spin.setToolTip("")

    def set_player_count(self, count: int):
        self.player_count = count
        if self.pairing_combo.currentData() == "round_robin":
            self.rounds_spin.setValue(max(1, count - 1))

    def on_rounds_changed(self, value):
        # Optionally, update player count if not round robin
        if self.pairing_combo.currentData() != "round_robin":
            self.player_count = value + 1  # For UI consistency
