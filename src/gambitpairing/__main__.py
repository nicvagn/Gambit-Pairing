import logging
import os
import sys

from PyQt6 import QtWidgets
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QStyle

from gambitpairing.gui.mainwindow import SwissTournamentApp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    """Entry point"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    exit_code = run_app()
    logging.info("run_app() exited with code: %s", exit_code)
    sys.exit(exit_code)

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and standard deployments"""
    return os.path.join(BASE_DIR, relative_path)

def get_cross_platform_icon():
    """
    Get application icon with cross-platform fallbacks:
    1. Try custom icons (ico, png)
    2. Try Qt theme icons
    3. Fall back to system standard icon
    """
    # First, try custom icons in preferred order
    icon_folder = resource_path(os.path.join("resources", "icons"))
    custom_icon_files = [
        "icon.png",    # Cross-platform
        "icon.ico",    # Windows preferred
    ]

    for icon_file in custom_icon_files:
        icon_path = os.path.join(icon_folder, icon_file)
        if os.path.exists(icon_path):
            logging.info(f"Using custom icon: {icon_path}")
            return QIcon(icon_path)

    # Try Qt theme icons (works well on Linux, limited on Windows/macOS)
    theme_icons = [
        "applications-games",
        "application-default-icon",
        "preferences-system",
        "applications-system"
    ]

    for theme_name in theme_icons:
        theme_icon = QIcon.fromTheme(theme_name)
        if not theme_icon.isNull():
            logging.info(f"Using theme icon: {theme_name}")
            return theme_icon

    # Fall back to Qt standard system icon
    logging.info("Using Qt standard system icon as fallback")
    return None  # Will be handled by get_icon_path()

def get_icon_path():
    """Get the icon path with cross-platform support"""
    # Try to get cross-platform icon first
    cross_platform_icon = get_cross_platform_icon()
    if cross_platform_icon:
        return cross_platform_icon

    return None

def set_application_icon(app):
    """Set application icon with multiple fallback strategies"""
    # Try to get custom or theme icon
    icon = get_icon_path()

    if icon and isinstance(icon, QIcon) and not icon.isNull():
        app.setWindowIcon(icon)
        logging.info("Successfully set application icon")
        return True

    # Final fallback: use Qt's standard application icon
    try:
        standard_icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        if not standard_icon.isNull():
            app.setWindowIcon(standard_icon)
            logging.info("Using Qt standard computer icon as fallback")
            return True

        # Alternative standard icons to try
        fallback_icons = [
            QStyle.StandardPixmap.SP_DesktopIcon,
            QStyle.StandardPixmap.SP_FileDialogDetailedView,
            QStyle.StandardPixmap.SP_DialogOkButton
        ]

        for fallback in fallback_icons:
            fallback_icon = app.style().standardIcon(fallback)
            if not fallback_icon.isNull():
                app.setWindowIcon(fallback_icon)
                logging.info(f"Using Qt standard icon: {fallback}")
                return True

    except Exception as e:
        logging.error(f"Error setting standard icon: {e}")

    logging.warning("No suitable application icon found")
    return False

def run_app():
    app = QtWidgets.QApplication(sys.argv)

    # Set cross-platform application icon
    set_application_icon(app)

    # Load stylesheet
    try:
        styles_qss = os.path.join(BASE_DIR, "resources", "styles.qss")
        with open(styles_qss, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        logging.error(f"Could not load stylesheet: {e}")

    try:
        # Try to apply a modern style if available
        available_styles = QtWidgets.QStyleFactory.keys()
        preferred_styles = ["Fusion", "WindowsVista", "Windows"]  # Cross-platform preferences

        for preferred_style in preferred_styles:
            if preferred_style in available_styles:
                app.setStyle(preferred_style)
                logging.info(f"Applied style: {preferred_style}")
                break

    except Exception as e:
        logging.warning(f"Could not set preferred application style: {e}")

    window = SwissTournamentApp()
    window.set_app_instance(app)
    window.show()
    window.show_about_dialog()

    exit_code = app.exec()
    return exit_code

if __name__ == "__main__":
    main()
