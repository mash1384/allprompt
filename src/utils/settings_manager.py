#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
설정 관리 모듈
애플리케이션 설정을 저장하고 로드하는 기능을 제공합니다.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import appdirs

logger = logging.getLogger(__name__)

# 애플리케이션 정보
APP_NAME = "allprompt"
APP_AUTHOR = "allprompt"
APP_VERSION = "0.1.0"

class SettingsManager:
    """애플리케이션 설정 관리 클래스"""
    
    def __init__(self):
        """설정 관리자 초기화"""
        self.settings_dir = Path(appdirs.user_config_dir(APP_NAME, APP_AUTHOR))
        self.settings_file = self.settings_dir / "settings.json"
        
        # 기본 설정값
        self.default_settings = {
            "show_hidden_files": False,
            "follow_symlinks": False,
            "apply_gitignore_rules": True,
            "copy_file_tree_only": False,
            "last_directory": str(Path.home()),
        }
        
        # 현재 설정 (초기값은 기본값으로 설정)
        self.settings = self.default_settings.copy()
        
        # 디렉토리 생성 (필요한 경우)
        self._ensure_settings_dir()
        
        # 설정 로드
        self.load_settings()
    
    def _ensure_settings_dir(self) -> None:
        """설정 디렉토리 존재 여부 확인 및 생성"""
        try:
            if not self.settings_dir.exists():
                self.settings_dir.mkdir(parents=True)
                logger.info(f"설정 디렉토리 생성: {self.settings_dir}")
        except Exception as e:
            logger.error(f"설정 디렉토리 생성 중 오류: {e}")
    
    def load_settings(self) -> None:
        """
        설정 파일에서 설정 로드
        로드 실패 시 기본값 사용
        """
        if not self.settings_file.exists():
            logger.info(f"설정 파일을 찾을 수 없음, 기본값 사용: {self.settings_file}")
            return
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                
            # 설정 업데이트 (기본값에 로드된 값 병합)
            self.settings.update(loaded_settings)
            logger.info(f"설정 로드 완료: {self.settings_file}")
        except json.JSONDecodeError:
            logger.error(f"설정 파일 형식 오류: {self.settings_file}")
        except Exception as e:
            logger.error(f"설정 로드 중 오류: {e}")
    
    def save_settings(self) -> bool:
        """
        현재 설정을 파일에 저장
        
        Returns:
            저장 성공 여부
        """
        try:
            # 설정 디렉토리 확인/생성
            self._ensure_settings_dir()
            
            # 설정 파일 저장
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            
            logger.info(f"설정 저장 완료: {self.settings_file}")
            return True
        except Exception as e:
            logger.error(f"설정 저장 중 오류: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        특정 설정값 반환
        
        Args:
            key: 설정 키
            default: 키가 없을 경우 반환할 기본값
            
        Returns:
            설정값 또는 기본값
        """
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """
        특정 설정값 설정
        
        Args:
            key: 설정 키
            value: 설정값
        """
        self.settings[key] = value
    
    def get_all_settings(self) -> Dict[str, Any]:
        """
        모든 설정값 반환
        
        Returns:
            설정 딕셔너리
        """
        return self.settings.copy()
    
    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        """
        여러 설정값 한 번에 업데이트
        
        Args:
            new_settings: 새 설정값 딕셔너리
        """
        self.settings.update(new_settings)
    
    def reset_to_defaults(self) -> None:
        """모든 설정을 기본값으로 초기화"""
        self.settings = self.default_settings.copy()
        logger.info("설정이 기본값으로 초기화됨") 