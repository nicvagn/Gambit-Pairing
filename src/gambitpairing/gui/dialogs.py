from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt
from typing import List, Optional, Tuple, Dict, Any
from gambitpairing.core.player import Player
from gambitpairing.core.constants import TIEBREAK_NAMES, DEFAULT_TIEBREAK_SORT_ORDER
from gambitpairing.core.utils import apply_stylesheet

# --- GUI Dialogs ---
# (No changes to PlayerEditDialog, PlayerDetailDialog, SettingsDialog, ManualPairDialog unless behaviorally impacted by core changes)
# PlayerDetailDialog: Default rating could be None, Player class handles default.
# SettingsDialog: Tiebreak order changes are reflected.


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
                "desc": "The most widely used Swiss system: players are grouped by score, then paired top-half vs bottom-half within each group, avoiding repeats and balancing colors. Used in FIDE and USCF events.",
                "fide": True,
                "uscf": True,
                "details": "<ul><li><b>Pairing Logic:</b> Players are sorted by score, then paired top vs bottom within each score group, avoiding previous opponents and balancing colors.</li><li><b>Best For:</b> Most open tournaments, FIDE/USCF events.</li><li><b>Notes:</b> This is the standard Swiss system for rated events.</li></ul>",
            },
            "round_robin": {
                "title": "Round Robin",
                "desc": "Every player plays every other player. Used for small events and FIDE title norm tournaments.",
                "fide": True,
                "uscf": True,
                "details": "<ul><li><b>Pairing Logic:</b> All-play-all, each player faces every other once.</li><li><b>Best For:</b> Small groups, title norm events, club championships.</li><li><b>Notes:</b> Number of rounds = number of players - 1.</li></ul>",
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
        apply_stylesheet(toc, "font-size: 11pt;")
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
        apply_stylesheet(
            title_label, "font-size: 15pt; font-weight: bold; margin-bottom: 6px;"
        )
        desc_label = QtWidgets.QLabel()
        desc_label.setWordWrap(True)
        apply_stylesheet(desc_label, "font-size: 11pt; margin-bottom: 8px;")
        html_details = QtWidgets.QTextBrowser()
        html_details.setOpenExternalLinks(True)
        apply_stylesheet(
            html_details,
            "background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px; font-size: 10.5pt;",
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


class PlayerDetailDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, player_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Player")
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit()
        self.rating_spin = QtWidgets.QSpinBox()
        self.rating_spin.setRange(0, 4000)  # Rating can be 0 (e.g. unrated)
        self.rating_spin.setValue(1000)  # Default if new

        # --- Make QSpinBox arrows black ---
        apply_stylesheet(
            self.rating_spin,
            """
            QAbstractSpinBox::up-button, QAbstractSpinBox::down-button,
            QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {
                qproperty-iconColor: #111;
            }
        """,
        )

        gender_dob_layout = QtWidgets.QHBoxLayout()
        self.gender_combo = QtWidgets.QComboBox()
        self.gender_combo.addItems(["", "Male", "Female"])
        self.gender_combo.setToolTip("Select gender (optional)")
        gender_dob_layout.addWidget(QtWidgets.QLabel("Gender:"))
        gender_dob_layout.addWidget(self.gender_combo)
        self.dob_edit = QtWidgets.QDateEdit()
        self.dob_edit.setCalendarPopup(True)
        self.dob_edit.setDisplayFormat("yyyy-MM-dd")
        # Allow null/empty date by default
        self.dob_edit.setSpecialValueText(" ")  # Show blank when date is not set
        self.dob_edit.setDate(QtCore.QDate())  # Start with an invalid/null date
        self.dob_edit.setToolTip("Select date of birth (optional)")

        # --- Make QDateEdit calendar button black ---
        apply_stylesheet(
            self.dob_edit,
            """
            QDateEdit::drop-down, QDateEdit::down-arrow, QDateEdit::calendarButton {
                qproperty-iconColor: #111;
            }
        """,
        )
        # self.calendar_popup = QtWidgets.QCalendarWidget() # QDateEdit has its own popup
        # self.calendar_popup.setGridVisible(True)
        # self.calendar_popup.setMaximumDate(QtCore.QDate.currentDate())
        # self.dob_edit.setCalendarWidget(self.calendar_popup)
        gender_dob_layout.addSpacing(10)
        gender_dob_layout.addWidget(QtWidgets.QLabel("Date of Birth:"))
        gender_dob_layout.addWidget(self.dob_edit)
        phone_layout = QtWidgets.QHBoxLayout()
        self.phone_edit = QtWidgets.QLineEdit()
        self.btn_copy_phone = QtWidgets.QPushButton()
        copy_icon = QtGui.QIcon.fromTheme("edit-copy")
        if not copy_icon.isNull():
            self.btn_copy_phone.setIcon(copy_icon)
        else:
            self.btn_copy_phone.setText("Copy")
        self.btn_copy_phone.setFixedWidth(40)
        self.btn_copy_phone.setToolTip("Copy phone number")
        self.btn_copy_phone.clicked.connect(
            lambda: self.copy_and_notify(self.phone_edit.text())
        )
        phone_layout.addWidget(self.phone_edit)
        phone_layout.addWidget(self.btn_copy_phone)
        email_layout = QtWidgets.QHBoxLayout()
        self.email_edit = QtWidgets.QLineEdit()
        self.btn_copy_email = QtWidgets.QPushButton()
        if not copy_icon.isNull():
            self.btn_copy_email.setIcon(copy_icon)
        else:
            self.btn_copy_email.setText("Copy")
        self.btn_copy_email.setFixedWidth(40)
        self.btn_copy_email.setToolTip("Copy email address")
        self.btn_copy_email.clicked.connect(
            lambda: self.copy_and_notify(self.email_edit.text())
        )
        email_layout.addWidget(self.email_edit)
        email_layout.addWidget(self.btn_copy_email)
        self.club_edit = QtWidgets.QLineEdit()
        self.federation_edit = QtWidgets.QLineEdit()
        form.addRow("Name:", self.name_edit)
        form.addRow("Rating:", self.rating_spin)
        form.addRow(gender_dob_layout)
        form.addRow("Phone:", phone_layout)
        form.addRow("Email:", email_layout)
        form.addRow("Club:", self.club_edit)
        form.addRow("Federation:", self.federation_edit)
        layout.addLayout(form)
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
        if player_data:
            self.name_edit.setText(player_data.get("name", ""))
            self.rating_spin.setValue(
                player_data.get("rating", 1000)
                if player_data.get("rating") is not None
                else 1000
            )
            gender = player_data.get("gender", "")
            idx = self.gender_combo.findText(gender) if gender else 0
            self.gender_combo.setCurrentIndex(idx if idx >= 0 else 0)
            dob_str = player_data.get("dob")
            if dob_str:
                q_date = QtCore.QDate.fromString(dob_str, "yyyy-MM-dd")
                if q_date.isValid():
                    self.dob_edit.setDate(q_date)
                else:
                    self.dob_edit.setDate(QtCore.QDate())  # Set to null if invalid
            else:
                self.dob_edit.setDate(QtCore.QDate())  # Set to null if not present

            self.phone_edit.setText(player_data.get("phone", "") or "")
            self.email_edit.setText(player_data.get("email", "") or "")
            self.club_edit.setText(player_data.get("club", "") or "")
            self.federation_edit.setText(player_data.get("federation", "") or "")

    def accept(self):
        if (
            self.dob_edit.date().isValid()
            and self.dob_edit.date() > QtCore.QDate.currentDate()
        ):
            QtWidgets.QMessageBox.warning(
                self, "Validation Error", "Date of birth cannot be in the future."
            )
            return
        super().accept()

    def get_player_data(self) -> Dict[str, Any]:
        dob_qdate = self.dob_edit.date()
        return {
            "name": self.name_edit.text().strip(),
            "rating": self.rating_spin.value(),
            "gender": (
                self.gender_combo.currentText()
                if self.gender_combo.currentText()
                else None
            ),
            "dob": dob_qdate.toString("yyyy-MM-dd") if dob_qdate.isValid() else None,
            "phone": self.phone_edit.text().strip() or None,
            "email": self.email_edit.text().strip() or None,
            "club": self.club_edit.text().strip() or None,
            "federation": self.federation_edit.text().strip() or None,
        }

    def copy_and_notify(self, text):
        QtWidgets.QApplication.clipboard().setText(text)
        self.show_copy_notification()

    def show_copy_notification(self):
        if hasattr(self, "_copy_notification") and self._copy_notification:
            self._copy_notification.close()
        self._copy_notification = QtWidgets.QLabel("Copied to clipboard!", self)
        apply_stylesheet(
            self._copy_notification,
            """
            QLabel {
                background: rgba(30,30,30,220);
                color: black;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 12pt;
                font-weight: bold;
                min-width: 180px;
                qproperty-alignment: AlignCenter;
            }
        """,
        )
        self._copy_notification.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.ToolTip
        )
        self._copy_notification.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TranslucentBackground
        )
        self._copy_notification.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating
        )
        self._copy_notification.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._copy_notification.adjustSize()
        geo = self.geometry()
        notif_geo = self._copy_notification.frameGeometry()
        x = geo.x() + (geo.width() - notif_geo.width()) // 2
        y = geo.y() + geo.height() - notif_geo.height() - 40
        self._copy_notification.move(x, y)
        self._copy_notification.setWindowOpacity(0.0)
        self._copy_notification.show()
        self._copy_notification.raise_()
        # Animation
        self._anim = QtCore.QPropertyAnimation(
            self._copy_notification, b"windowOpacity", self
        )
        self._anim.setDuration(200)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.finished.connect(
            lambda: QtCore.QTimer.singleShot(900, self.fade_out_copy_notification)
        )
        self._anim.start()

    def fade_out_copy_notification(self):
        if hasattr(self, "_copy_notification") and self._copy_notification:
            anim = QtCore.QPropertyAnimation(
                self._copy_notification, b"windowOpacity", self
            )
            anim.setDuration(400)
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
            anim.finished.connect(self._copy_notification.close)
            anim.start()


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, num_rounds: int, tiebreak_order: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tournament Settings")
        self.setMinimumWidth(350)
        self.current_tiebreak_order = list(tiebreak_order)
        layout = QtWidgets.QVBoxLayout(self)
        rounds_group = QtWidgets.QGroupBox("General")
        rounds_layout = QtWidgets.QFormLayout(rounds_group)
        self.spin_num_rounds = QtWidgets.QSpinBox()
        self.spin_num_rounds.setRange(1, 50)
        self.spin_num_rounds.setValue(num_rounds)
        self.spin_num_rounds.setToolTip("Set the total number of rounds.")
        rounds_layout.addRow("Number of Rounds:", self.spin_num_rounds)
        layout.addWidget(rounds_group)
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
        layout.addWidget(tiebreak_group)
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
            self.update_order_from_list()

    def move_tiebreak_down(self):
        current_row = self.tiebreak_list.currentRow()
        if current_row < self.tiebreak_list.count() - 1:
            item = self.tiebreak_list.takeItem(current_row)
            self.tiebreak_list.insertItem(current_row + 1, item)
            self.tiebreak_list.setCurrentRow(current_row + 1)
            self.update_order_from_list()

    def update_order_from_list(self):
        self.current_tiebreak_order = [
            self.tiebreak_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.tiebreak_list.count())
        ]

    def accept(self):
        self.update_order_from_list()
        super().accept()

    def get_settings(self) -> Tuple[int, List[str]]:
        return self.spin_num_rounds.value(), self.current_tiebreak_order


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
