#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
액션 컨트롤러 모듈
주요 사용자 액션의 로직을 처리하는 컨트롤러를 정의합니다.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Union, Tuple

from PySide6.QtCore import Qt, QObject, Signal

# 코어 모듈 임포트
from src.core.file_scanner import is_binary_file, read_text_file
from src.core.output_formatter import generate_full_output
from src.utils.clipboard_utils import copy_to_clipboard

logger = logging.getLogger(__name__)


class ActionController(QObject):
    """
    액션 컨트롤러
    UI와 분리된 주요 사용자 액션의 로직을 처리합니다.
    """
    
    # 시그널 정의
    copy_status_signal = Signal(bool, str)  # 복사 상태 시그널 (성공 여부, 메시지)
    
    def __init__(self):
        """ActionController 초기화"""
        super().__init__()
    
    def perform_copy_to_clipboard(self, root_path, selected_item_details, total_tokens, copy_file_tree_only=False):
        """
        선택된 파일 내용을 클립보드에 복사하는 액션 수행
        
        Args:
            root_path: 프로젝트 루트 경로
            selected_item_details: 선택된 항목의 세부 정보 목록
            total_tokens: 총 토큰 수
            copy_file_tree_only: 파일트리만 복사할지 여부 (기본값: False)
            
        Returns:
            복사 성공 여부 (boolean)
        """
        try:
            # 선택된 항목 중 텍스트 파일만 필터링
            text_files = []
            
            for item_path in selected_item_details:
                path = Path(item_path)
                if path.is_file() and not is_binary_file(path):
                    text_files.append(path)
            
            # 텍스트 파일이 없는 경우
            if not text_files:
                self.copy_status_signal.emit(False, "선택된 항목 중 텍스트 파일이 없습니다.")
                return False
            
            # 선택된 항목 상세 정보 구성
            items_details = []
            total_files = 0
            
            for file_path in text_files:
                path_str = str(file_path)
                
                # 파일 읽기 (파일트리만 복사 옵션이 아닐 때만)
                if not copy_file_tree_only:
                    content = read_text_file(file_path)
                    
                    # 오류 정보가 포함된 딕셔너리인 경우 처리
                    if isinstance(content, dict) and 'error' in content:
                        error_msg = f"{file_path} 파일을 읽는 중 오류가 발생했습니다: {content['error']}"
                        self.copy_status_signal.emit(False, error_msg)
                        continue
                
                # 파일 항목 추가
                rel_path = file_path.relative_to(root_path)
                items_details.append({
                    'path': file_path,
                    'rel_path': rel_path,
                    'is_dir': False
                })
                total_files += 1
            
            # 클립보드에 복사
            if items_details:
                # 전체 출력 생성
                formatted_text = generate_full_output(root_path, items_details, copy_file_tree_only=copy_file_tree_only)
                
                # 클립보드에 복사
                success = copy_to_clipboard(formatted_text)
                
                if success:
                    # 복사 성공 메시지
                    if copy_file_tree_only:
                        success_msg = f"Copied file tree of {total_files} files to clipboard (file contents excluded)"
                    else:
                        success_msg = f"Copied {total_files} files ({total_tokens:,} tokens) to clipboard"
                    self.copy_status_signal.emit(True, success_msg)
                    logger.info(success_msg)
                    return True
                else:
                    # 복사 실패 메시지
                    self.copy_status_signal.emit(False, "클립보드 복사 실패")
                    return False
            else:
                # 복사할 내용이 없는 경우
                self.copy_status_signal.emit(False, "복사할 내용이 없습니다.")
                return False
                
        except Exception as e:
            # 예외 처리
            self.copy_status_signal.emit(False, str(e))
            logger.error(f"Copy error: {str(e)}", exc_info=True)
            return False 