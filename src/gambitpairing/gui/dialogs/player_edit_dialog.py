from typing import Tuple

from PyQt6 import QtWidgets


class PlayerEditDialog(QtWidgets.QDialog):
    def __init__(
        self, player_name: str, player_rating: int, player_active: bool, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Edit Player")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.name_edit = QtWidgets.QLineEdit(player_name)
        self.rating_spin = QtWidgets.QSpinBox()
        self.rating_spin.setRange(0, 4000)
        self.rating_spin.setValue(
            player_rating if player_rating is not None else 1000
        )  # Handle None rating
        self.active_check = QtWidgets.QCheckBox("Active")
        self.active_check.setChecked(player_active)
        self.active_check.setToolTip("Uncheck to mark player as withdrawn.")
        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Name:", self.name_edit)
        form_layout.addRow("Rating:", self.rating_spin)
        form_layout.addRow(self.active_check)
        self.layout.addLayout(form_layout)
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

    def get_data(self) -> Tuple[str, int, bool]:
        name = self.name_edit.text().strip()
        rating = self.rating_spin.value()
        is_active = self.active_check.isChecked()
        return name, rating, is_active
