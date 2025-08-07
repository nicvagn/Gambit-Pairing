from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional


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
        self.rating_spin.setStyleSheet("""
            QAbstractSpinBox::up-button, QAbstractSpinBox::down-button,
            QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {
                qproperty-iconColor: #111;
            }
        """)

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
        self.dob_edit.setStyleSheet("""
            QDateEdit::drop-down, QDateEdit::down-arrow, QDateEdit::calendarButton {
                qproperty-iconColor: #111;
            }
        """)
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
        self._copy_notification.setStyleSheet("""
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
        """)
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
