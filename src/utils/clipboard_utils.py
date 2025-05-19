#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
클립보드 유틸리티 모듈
시스템 클립보드와 관련된 작업을 처리하는 유틸리티 함수를 제공합니다.
두 가지 방식(pyperclip과 PySide6.QtGui.QClipboard)을 지원하여 macOS Sandbox 환경에서도 동작하도록 합니다.
"""

import logging
from typing import Optional
import sys

# pyperclip 임포트 시도 (기본 방식)
try:
    import pyperclip
    has_pyperclip = True
except ImportError:
    has_pyperclip = False

# PySide6 임포트 시도 (대체 방식)
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QClipboard
    has_pyside6 = True
except ImportError:
    has_pyside6 = False

logger = logging.getLogger(__name__)

# QApplication 인스턴스 확인 및 필요시 생성 함수
def ensure_qt_application():
    """PySide6 QApplication 인스턴스가 존재하는지 확인하고, 없으면 생성"""
    if has_pyside6:
        if not QApplication.instance():
            # 경고: 이 방식은 일반적으로 권장되지 않으나, 클립보드 작업만을 위한 최소한의 설정
            app = QApplication(sys.argv)
            logger.debug("QApplication 인스턴스 생성됨")
            return app
        return QApplication.instance()
    return None

def copy_to_clipboard(text: str) -> bool:
    """
    텍스트를 시스템 클립보드에 복사 (여러 방식 시도)
    
    Args:
        text: 클립보드에 복사할 텍스트
        
    Returns:
        복사 성공 여부
    """
    # PySide6 방식 먼저 시도 (macOS에서 더 안정적일 수 있음)
    if has_pyside6:
        try:
            app = ensure_qt_application()
            clipboard = app.clipboard()
            clipboard.setText(text)
            logger.info(f"PySide6 방식으로 클립보드에 텍스트 복사 성공 ({len(text)} 문자)")
            return True
        except Exception as e:
            logger.warning(f"PySide6 클립보드 복사 실패, pyperclip 시도 예정: {e}")
            # PySide6 방식 실패 시 pyperclip으로 대체
    
    # pyperclip 방식 시도
    if has_pyperclip:
        try:
            pyperclip.copy(text)
            logger.info(f"pyperclip 방식으로 클립보드에 텍스트 복사 성공 ({len(text)} 문자)")
            return True
        except Exception as e:
            logger.error(f"클립보드 복사 중 오류 (pyperclip): {e}")
    else:
        logger.error("클립보드 복사 실패: 지원되는 클립보드 모듈이 없습니다.")
    
    return False

def get_from_clipboard() -> Optional[str]:
    """
    시스템 클립보드에서 텍스트 가져오기 (여러 방식 시도)
    
    Returns:
        클립보드 내용 또는 오류 시 None
    """
    # PySide6 방식 먼저 시도
    if has_pyside6:
        try:
            app = ensure_qt_application()
            clipboard = app.clipboard()
            text = clipboard.text()
            logger.debug(f"PySide6 방식으로 클립보드에서 텍스트 가져오기 성공 ({len(text)} 문자)")
            return text
        except Exception as e:
            logger.warning(f"PySide6 클립보드 읽기 실패, pyperclip 시도 예정: {e}")
    
    # pyperclip 방식 시도
    if has_pyperclip:
        try:
            text = pyperclip.paste()
            logger.debug(f"pyperclip 방식으로 클립보드에서 텍스트 가져오기 성공 ({len(text)} 문자)")
            return text
        except Exception as e:
            logger.error(f"클립보드에서 텍스트 가져오기 중 오류 (pyperclip): {e}")
    else:
        logger.error("클립보드 읽기 실패: 지원되는 클립보드 모듈이 없습니다.")
    
    return None 