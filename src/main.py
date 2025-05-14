#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM 프롬프트용 코드 스니펫 생성 도우미
애플리케이션 진입점
"""

import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream # QTextStream 임포트 추가
from src.gui.main_window import MainWindow
from src.gui.resources import resources # 컴파일된 리소스 임포트

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

        # --------------------------------------------------
        # 스타일시트 로드 및 적용 코드 추가
        # --------------------------------------------------
        qss_file = QFile(":/styles/style.qss") # 리소스 경로 사용 (resources.qrc의 prefix와 파일 경로 조합)
        if qss_file.open(QFile.ReadOnly | QFile.Text):
            stream = QTextStream(qss_file)
            app.setStyleSheet(stream.readAll()) # 애플리케이션 전체에 스타일 적용
            qss_file.close()
            logger.info("스타일시트 로드 및 적용 완료.")
        else:
            logger.error(f"스타일시트 파일을 열 수 없습니다: {qss_file.errorString()}")
        # --------------------------------------------------

        window = MainWindow()
        window.show()

        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"애플리케이션 실행 중 오류 발생: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()