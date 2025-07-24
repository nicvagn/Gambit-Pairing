import sys
from PyQt6 import QtWidgets
from PyQt6.QtGui import QIcon
from gui.mainwindow import SwissTournamentApp
from core.utils import style_manager
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    def run_app():
        app = QtWidgets.QApplication(sys.argv)
        app.setWindowIcon(QIcon("icon.ico"))  # Set the application icon
        
        # Check if legacy mode is enabled before loading stylesheet
        legacy_mode = style_manager.load_legacy_setting()
        
        if not legacy_mode:
            # load stylesheet only if not in legacy mode
            try:
                with open("styles.qss", "r", encoding="utf-8") as f:
                    app.setStyleSheet(f.read())
            except Exception as e:
                logging.error(f"Could not load stylesheet: {e}")
        else:
            logging.info("Legacy GUI mode enabled - skipping stylesheet loading")
            
        try: 
            # Try to apply a modern style if available (and not in legacy mode)
            available_styles = QtWidgets.QStyleFactory.keys()
            if "Fusion" in available_styles and not legacy_mode:
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

