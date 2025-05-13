#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM 프롬프트용 코드 스니펫 생성 도우미
애플리케이션 진입점
"""

import sys
import logging
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow

# 로깅 설정
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
    """애플리케이션 메인 함수"""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("LLM 프롬프트 헬퍼")
        
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"애플리케이션 실행 중 오류 발생: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 