#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Prompt Helper
Application entry point
"""

import sys
import os
import logging
from pathlib import Path

# Add project root directory to sys.path
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream
from src.gui.main_window import MainWindow
from src.gui.resources import resources # Import compiled resources

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Application main function"""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("LLM Prompt Helper")

        # --------------------------------------------------
        # Load and apply stylesheet
        # --------------------------------------------------
        qss_file = QFile(":/styles/style.qss") # Use resource path (combined from prefix and file path in resources.qrc)
        if qss_file.open(QFile.ReadOnly | QFile.Text):
            stream = QTextStream(qss_file)
            app.setStyleSheet(stream.readAll()) # Apply style to the entire application
            qss_file.close()
            logger.info("Stylesheet loaded and applied.")
        else:
            logger.error(f"Could not open stylesheet file: {qss_file.errorString()}")
        # --------------------------------------------------

        window = MainWindow()
        window.show()

        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Error during application execution: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()