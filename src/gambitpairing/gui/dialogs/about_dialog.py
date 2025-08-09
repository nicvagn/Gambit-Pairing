"""About dialog for Gambit Pairing"""

# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gambitpairing.core.constants import APP_NAME, APP_VERSION


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for cx_Freeze"""
    if getattr(sys, "frozen", False):
        # The application is frozen
        base_path = os.path.dirname(sys.executable)
    else:
        # The application is not frozen - go up from dialogs dir to project root
        # Current file is in src/gambitpairing/gui/dialogs/
        # So we need to go up 4 levels to reach project root
        base_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
        )

    return os.path.join(base_path, relative_path)


class AboutDialog(QDialog):
    """Modern about dialog with tabbed interface showing app info and license."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumSize(320, 260)
        self.resize(340, 280)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the modern tabbed user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create tab widget
        tab_widget = QTabWidget()
        tab_widget.addTab(self._create_about_tab(), "About")
        tab_widget.addTab(self._create_license_tab(), "License")

        main_layout.addWidget(tab_widget)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 15, 20, 20)
        button_layout.addStretch()

        ok_button = QPushButton("Close")
        ok_button.clicked.connect(self.accept)
        ok_button.setMinimumWidth(100)
        ok_button.setStyleSheet("font-weight: 500;")
        button_layout.addWidget(ok_button)

        main_layout.addLayout(button_layout)

    def _create_about_tab(self) -> QWidget:
        """Create the About tab with app information."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 12, 16, 8)

        # Subtle separator line
        sep1 = QLabel()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet("background: #e3e7ee; margin: 8px 0 8px 0;")

        # Load and display about image
        self._add_about_image(layout)

        # App name and version in a single concise header
        header_label = QLabel(
            f"<span style='font-size:18pt; font-weight:700; color:#2d5a27;'>{APP_NAME}</span> <span style='font-size:11pt; color:#6b7280; font-weight:400;'>v{APP_VERSION}</span>"
        )
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("margin-bottom: 4px;")
        layout.addWidget(header_label)

        # Subtitle
        subtitle_label = QLabel("Chess Tournament Manager")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet(
            "color: #8b5c2b; font-size:9pt; font-style:italic; margin-bottom: 10px;"
        )
        layout.addWidget(subtitle_label)

        layout.addWidget(sep1)
        # Subtle separator after description
        sep2 = QLabel()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: #e3e7ee; margin: 8px 0 8px 0;")

        # Description block
        description_text = (
            "<div style='color:#23272f; font-size:10pt; line-height:1.5; padding:12px 10px; background:#f9fafb; border-radius:8px; border:1px solid #e3e7ee;'>"
            "Fast, fair, and modern tournament management.<br>"
            "Open source and cross-platform<br>"
            "<span style='font-weight:600; color:#2d5a27;'>Copyright © 2025 Gambit Group</span><br>"
            "Developed by <span style='font-weight:600;'>Chickaboo</span> and <span style='font-weight:600;'>Nic</span>"
            "</div>"
        )
        description_label = QLabel(description_text)
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)
        description_label.setStyleSheet("margin-bottom: 8px;")
        layout.addWidget(description_label)
        layout.addWidget(sep2)

        # Support links block
        support_text = (
            "<div style='color:#6b7280; font-size:9pt; padding:8px; background:#fff; border-radius:7px; border:1px solid #e3e7ee;'>"
            "For support, join our <a href='https://discord.gg/eEnnetMDfr' style='color:#2d5a27; font-weight:600; text-decoration:none;'>Discord community</a><br>"
            "or visit <a href='https://www.chickaboo.net/contact' style='color:#2d5a27; font-weight:600; text-decoration:none;'>chickaboo.net/contact</a>"
            "</div>"
        )
        support_label = QLabel(support_text)
        support_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        support_label.setOpenExternalLinks(True)
        support_label.setWordWrap(True)
        support_label.setStyleSheet("margin-bottom: 4px;")
        layout.addWidget(support_label)

        layout.addStretch()
        return tab

    def _create_license_tab(self) -> QWidget:
        """Create the License tab with GNU GPL v3 text."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # License header
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 20, 20, 15)

        license_title = QLabel("GNU General Public License v3")
        license_font = QFont()
        license_font.setPointSize(14)
        license_font.setBold(True)
        license_title.setFont(license_font)
        license_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        license_title.setStyleSheet("color: #2d5a27; margin-bottom: 5px;")
        header_layout.addWidget(license_title)

        license_subtitle = QLabel("This software is licensed under the GNU GPL v3")
        license_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        license_subtitle.setStyleSheet("color: #6b7280; font-size: 10pt;")
        header_layout.addWidget(license_subtitle)

        layout.addWidget(header_widget)

        # License text in scrollable area
        license_text = self._get_license_text()
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(license_text)
        text_edit.setStyleSheet("font-size: 9pt; line-height: 1.3;")
        layout.addWidget(text_edit)
        return tab

    def _add_about_image(self, layout):
        """Add the about image to the layout with fallback options."""
        # For images, go up 2 levels to src/gambitpairing
        base_img_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        image_path = os.path.join(base_img_path, "resources", "icons", "about.webp")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                img_label = QLabel()
                # Use fast transformation for pixelated look
                img_label.setPixmap(
                    pixmap.scaledToWidth(220, Qt.TransformationMode.FastTransformation)
                )
                img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img_label.setStyleSheet("margin-bottom: 8px;")
                layout.addWidget(img_label)
                return

    def _get_license_text(self) -> str:
        """Get the GNU GPL v3 license text from the license file."""
        license_path = resource_path(os.path.join("licenses", "LICENSE"))
        try:
            with open(license_path, "r", encoding="utf-8") as f:
                return f.read()
        except (FileNotFoundError, IOError):
            return (
                "GNU GENERAL PUBLIC LICENSE\n"
                "Version 3, 29 June 2007\n\n"
                "Copyright (C) 2025 Gambit Pairing developers\n\n"
                "This program is free software: you can redistribute it and/or modify "
                "it under the terms of the GNU General Public License as published by "
                "the Free Software Foundation\n\n"
                "This program is distributed in the hope that it will be useful, "
                "but WITHOUT ANY WARRANTY; without even the implied warranty of "
                "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the "
                "GNU General Public License for more details.\n\n"
                "You should have received a copy of the GNU General Public License "
                "along with this program. If not, see https://www.gnu.org/licenses/gpl-3.0.html .\n\n"
            )
