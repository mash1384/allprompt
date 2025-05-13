#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
클립보드 유틸리티 모듈
시스템 클립보드와 관련된 작업을 처리하는 유틸리티 함수를 제공합니다.
"""

import logging
from typing import Optional

import pyperclip

logger = logging.getLogger(__name__)

def copy_to_clipboard(text: str) -> bool:
    """
    텍스트를 시스템 클립보드에 복사
    
    Args:
        text: 클립보드에 복사할 텍스트
        
    Returns:
        복사 성공 여부
    """
    try:
        pyperclip.copy(text)
        logger.info(f"클립보드에 텍스트 복사 성공 ({len(text)} 문자)")
        return True
    except Exception as e:
        logger.error(f"클립보드 복사 중 오류: {e}")
        return False

def get_from_clipboard() -> Optional[str]:
    """
    시스템 클립보드에서 텍스트 가져오기
    
    Returns:
        클립보드 내용 또는 오류 시 None
    """
    try:
        text = pyperclip.paste()
        logger.debug(f"클립보드에서 텍스트 가져오기 성공 ({len(text)} 문자)")
        return text
    except Exception as e:
        logger.error(f"클립보드에서 텍스트 가져오기 중 오류: {e}")
        return None 