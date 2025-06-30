import sys
from PyQt6 import QtWidgets
from PyQt6.QtGui import QIcon
from gui.mainwindow import SwissTournamentApp
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QIcon("resources/icons/icon2.webp"))
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
        elif "WindowsVista" in available_styles and sys.platform == "win32": # Windows specific
            app.setStyle("WindowsVista")
    except Exception as e: 
        logging.warning(f"Could not set preferred application style: {e}")

    window = SwissTournamentApp()
    window.set_app_instance(app)
    window.show()
    window.show_about_dialog()
    sys.exit(app.exec())

