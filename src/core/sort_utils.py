#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
정렬 유틸리티 모듈
파일 및 폴더 항목을 정렬하는 기능을 제공합니다.
"""

import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

def sort_items(items: List[Dict[str, Any]], sort_by: str = "name", reverse: bool = False) -> List[Dict[str, Any]]:
    """
    파일 및 폴더 항목 목록을 정렬합니다.
    
    Args:
        items: 정렬할 항목 목록
        sort_by: 정렬 기준 ("name", "size", "type", "date" 등)
        reverse: 역순 정렬 여부
        
    Returns:
        정렬된 항목 목록
    """
    logger.debug(f"항목 정렬: {sort_by}, 역순={reverse}")
    
    # 폴더 먼저 정렬하기 위한 키 함수
    def sort_key(item):
        is_dir = item.get("is_dir", False)
        
        if sort_by == "name":
            return (not is_dir, item.get("name", "").lower())
        elif sort_by == "size":
            return (not is_dir, item.get("size", 0))
        elif sort_by == "type":
            # 확장자 기준 정렬
            name = item.get("name", "")
            ext = Path(name).suffix.lower() if name else ""
            return (not is_dir, ext, name.lower())
        elif sort_by == "date":
            return (not is_dir, item.get("modified", 0))
        else:
            # 기본값은 이름순
            return (not is_dir, item.get("name", "").lower())
    
    try:
        return sorted(items, key=sort_key, reverse=reverse)
    except Exception as e:
        logger.error(f"항목 정렬 중 오류 발생: {e}")
        return items  # 오류 발생 시 원본 목록 반환 