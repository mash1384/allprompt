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
import appdirs # appdirs 임포트

# Add project root directory to sys.path
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream
from src.gui.main_window import MainWindow
from src.gui.resources import resources # Import compiled resources

# Configure logging
APP_NAME = "allprompt"
APP_AUTHOR = "allprompt" # SettingsManager와 일관되게 (또는 원하는 이름으로)

try:
    log_dir = Path(appdirs.user_log_dir(APP_NAME, APP_AUTHOR))
    log_dir.mkdir(parents=True, exist_ok=True) # 로그 디렉토리 생성
    log_file_path = log_dir / "app.log"

    # 파일 핸들러 설정
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    # (선택) 스트림 핸들러 (터미널에도 로그 출력, 디버깅 시 유용)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    # root_logger.addHandler(stream_handler) # 필요에 따라 주석 해제 또는 유지

    logger = logging.getLogger(__name__) # 현재 모듈 로거 가져오기

except Exception as e:
    # 로그 설정 실패 시 최소한의 콘솔 출력
    print(f"Error setting up logging to file: {e}", file=sys.stderr)
    # 파일 로깅 실패 시 기본 콘솔 로깅만 사용
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])
    logger = logging.getLogger(__name__)


def main():
    """Application main function"""
    logger.info("Application starting...") # 앱 시작 로그 추가
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("allprompt")

        # --------------------------------------------------
        # Load and apply stylesheet
        # --------------------------------------------------
        qss_file = QFile(":/styles/style.qss")
        if qss_file.open(QFile.ReadOnly | QFile.Text):
            stream = QTextStream(qss_file)
            app.setStyleSheet(stream.readAll())
            qss_file.close()
            logger.info("Stylesheet loaded and applied.")
        else:
            logger.error(f"Could not open stylesheet file: {qss_file.errorString()}")
        # --------------------------------------------------

        window = MainWindow()
        window.show()
        logger.info("Main window shown. Starting event loop.") # 이벤트 루프 시작 전 로그

        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Unhandled error during application execution: {e}", exc_info=True)
        # (선택사항) 사용자에게 오류 메시지 박스 표시
        # from PySide6.QtWidgets import QMessageBox
        # msg_box = QMessageBox()
        # msg_box.setIcon(QMessageBox.Critical)
        # msg_box.setText("An unexpected error occurred.")
        # msg_box.setInformativeText(str(e))
        # msg_box.setWindowTitle("Application Error")
        # msg_box.exec_()
        sys.exit(1)

if __name__ == "__main__":
    main()