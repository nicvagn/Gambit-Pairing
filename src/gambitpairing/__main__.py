import logging
import os
import sys

from PyQt6 import QtWidgets
from PyQt6.QtGui import QIcon

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

def resource_path(relative_path) -> str:
    """Get absolute path to resource, works for dev and standard deployments"""
    return os.path.join(BASE_DIR, relative_path)

def get_icon_path() -> str | None:
    """Get the icon path. Works with standard deployments"""
    icon_folder = resource_path(os.path.join("resources", "icons"))
    ico_path = os.path.join(icon_folder, "icon.ico")
    png_path = os.path.join(icon_folder, "icon.png")

    if os.path.exists(ico_path):
        return ico_path
    elif os.path.exists(png_path):
        return png_path
    return None

def run_app() -> int:
    """Run app and return exit status code"""
    app = QtWidgets.QApplication(sys.argv)

    icon_path = get_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
    else:
        logging.warning("App icon not found in resources/icons.")

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
        if "WindowsVista" in available_styles:
            app.setStyle("WindowsVista")
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
