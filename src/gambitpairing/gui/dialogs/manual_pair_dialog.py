from PyQt6 import QtWidgets
from typing import List, Optional
from gambitpairing.core.player import Player


class ManualPairDialog(QtWidgets.QDialog):
    def __init__(
        self,
        player_name: str,
        current_opponent_name: str,
        available_opponents: List[Player],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Adjust Pairing for {player_name}")
        self.setMinimumWidth(300)
        self.available_opponents = available_opponents
        self.selected_opponent_id = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(f"Current Opponent: {current_opponent_name}"))
        layout.addWidget(QtWidgets.QLabel("Select New Opponent:"))
        self.opponent_combo = QtWidgets.QComboBox()
        self.opponent_combo.addItem("", None)
        for opp in sorted(available_opponents, key=lambda p: p.name):
            self.opponent_combo.addItem(f"{opp.name} ({opp.rating})", opp.id)
        layout.addWidget(self.opponent_combo)
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
        layout.addWidget(self.buttons)

    def accept(self):
        self.selected_opponent_id = self.opponent_combo.currentData()
        if not self.selected_opponent_id:
            QtWidgets.QMessageBox.warning(
                self, "Selection Error", "Please select a new opponent."
            )
            return
        super().accept()

    def get_selected_opponent_id(self) -> Optional[str]:
        return self.selected_opponent_id
