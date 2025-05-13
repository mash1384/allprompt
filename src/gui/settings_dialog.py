#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
설정 다이얼로그 모듈
애플리케이션 설정 관리를 위한 UI 컴포넌트입니다.
"""

import logging
from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QCheckBox, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal

from core.tokenizer import Tokenizer

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """애플리케이션 설정 다이얼로그"""
    
    # 설정 변경 시그널
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None, current_settings=None):
        """
        설정 다이얼로그 초기화
        
        Args:
            parent: 부모 위젯
            current_settings: 현재 설정 값 딕셔너리
        """
        super().__init__(parent)
        
        self.setWindowTitle("설정")
        self.setMinimumWidth(400)
        
        # 기본 설정값
        self.default_settings = {
            "model_name": "gpt-3.5-turbo",
            "show_hidden_files": False,
            "follow_symlinks": False,
        }
        
        # 현재 설정값
        self.current_settings = current_settings or self.default_settings.copy()
        
        # UI 초기화
        self._init_ui()
    
    def _init_ui(self):
        """UI 구성 요소 초기화"""
        # 메인 레이아웃
        layout = QVBoxLayout(self)
        
        # ===== 토큰화 모델 설정 그룹 =====
        model_group = QGroupBox("토큰화 모델 설정")
        model_layout = QFormLayout(model_group)
        
        # 모델 선택 콤보 박스
        self.model_combo = QComboBox()
        
        # 사용 가능한 모델 목록 가져오기
        tokenizer = Tokenizer()
        available_models = tokenizer.get_available_models()
        self.model_combo.addItems(available_models)
        
        # 현재 설정값으로 콤보 박스 설정
        current_model = self.current_settings.get("model_name")
        if current_model in available_models:
            self.model_combo.setCurrentText(current_model)
        
        model_layout.addRow("토큰화 모델:", self.model_combo)
        layout.addWidget(model_group)
        
        # ===== 파일 스캔 설정 그룹 =====
        scan_group = QGroupBox("파일 스캔 설정")
        scan_layout = QVBoxLayout(scan_group)
        
        # 숨김 파일 표시 체크박스
        self.show_hidden_files_cb = QCheckBox("숨김 파일/폴더 표시")
        self.show_hidden_files_cb.setChecked(self.current_settings.get("show_hidden_files", False))
        scan_layout.addWidget(self.show_hidden_files_cb)
        
        # 심볼릭 링크 따라가기 체크박스
        self.follow_symlinks_cb = QCheckBox("심볼릭 링크 따라가기 (위험할 수 있음)")
        self.follow_symlinks_cb.setChecked(self.current_settings.get("follow_symlinks", False))
        scan_layout.addWidget(self.follow_symlinks_cb)
        
        layout.addWidget(scan_group)
        
        # ===== 버튼 영역 =====
        button_layout = QHBoxLayout()
        
        # 기본값 버튼
        reset_button = QPushButton("기본값으로 복원")
        reset_button.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(reset_button)
        
        # 스트레치 추가 (버튼 사이 간격)
        button_layout.addStretch()
        
        # 취소/확인 버튼
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        save_button = QPushButton("저장")
        save_button.clicked.connect(self._save_settings)
        save_button.setDefault(True)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
    
    def _reset_to_defaults(self):
        """설정을 기본값으로 복원"""
        # 모델 선택 콤보 박스
        if self.default_settings["model_name"] in [self.model_combo.itemText(i) for i in range(self.model_combo.count())]:
            self.model_combo.setCurrentText(self.default_settings["model_name"])
        
        # 체크박스
        self.show_hidden_files_cb.setChecked(self.default_settings["show_hidden_files"])
        self.follow_symlinks_cb.setChecked(self.default_settings["follow_symlinks"])
    
    def _save_settings(self):
        """설정 저장 및 변경 시그널 발생"""
        settings = {
            "model_name": self.model_combo.currentText(),
            "show_hidden_files": self.show_hidden_files_cb.isChecked(),
            "follow_symlinks": self.follow_symlinks_cb.isChecked(),
        }
        
        # 설정이 변경되었는지 확인
        if settings != self.current_settings:
            logger.info("설정 변경: %s", settings)
            self.current_settings = settings
            self.settings_changed.emit(settings)
        
        self.accept()
    
    def get_settings(self) -> Dict[str, Any]:
        """
        현재 설정값 반환
        
        Returns:
            현재 설정값 딕셔너리
        """
        return self.current_settings 