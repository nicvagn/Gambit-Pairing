import sys
from PyQt6 import QtWidgets
from PyQt6.QtGui import QIcon
from gui.mainwindow import SwissTournamentApp
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    def run_app():
        app = QtWidgets.QApplication(sys.argv)
        app.setWindowIcon(QIcon("icon.ico"))  # Set the application icon
        # load stylesheet
        try:
            with open("styles.qss", "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            logging.error(f"Could not load stylesheet: {e}")
        try: 
            # Try to apply a modern style if available
            available_styles = QtWidgets.QStyleFactory.keys()
            if "Fusion" in available_styles:
                app.setStyle("WindowsVista")
        except Exception as e: 
            logging.warning(f"Could not set preferred application style: {e}")

        window = SwissTournamentApp()
        window.set_app_instance(app)
        window.show()
        window.show_about_dialog()
        exit_code = app.exec()
        return exit_code

    exit_code = run_app()
    sys.exit(exit_code)

