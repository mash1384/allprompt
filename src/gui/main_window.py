#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
메인 윈도우 모듈
애플리케이션의 주요 UI 구성 요소를 정의합니다.
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QFileDialog, QTreeView, QStatusBar,
    QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, QSize, QDir, Signal, Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """메인 애플리케이션 윈도우"""
    
    def __init__(self):
        """메인 윈도우 초기화"""
        super().__init__()
        
        self.setWindowTitle("LLM 프롬프트 헬퍼")
        self.setMinimumSize(800, 600)
        
        # 상태 정보 초기화
        self.current_folder = None
        
        self._init_ui()
        logger.info("메인 윈도우 초기화 완료")
    
    def _init_ui(self):
        """UI 구성 요소 초기화"""
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        
        # 스플리터 생성 (좌: 트리 뷰, 우: 제어 패널)
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # 좌측 패널 (트리 뷰)
        self.tree_view = QTreeView()
        self.tree_view.setMinimumWidth(300)
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["파일/폴더"])
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setEditTriggers(QTreeView.NoEditTriggers)
        self.splitter.addWidget(self.tree_view)
        
        # 우측 패널 (제어 버튼 및 정보)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.splitter.addWidget(right_panel)
        
        # 폴더 열기 버튼
        self.open_folder_btn = QPushButton("폴더 열기")
        self.open_folder_btn.clicked.connect(self._open_folder_dialog)
        right_layout.addWidget(self.open_folder_btn)
        
        # 토큰 정보 레이블
        self.token_label = QLabel("선택된 항목 없음")
        self.token_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.token_label)
        
        # 복사 버튼
        self.copy_btn = QPushButton("클립보드에 복사")
        self.copy_btn.setEnabled(False)
        right_layout.addWidget(self.copy_btn)
        
        # 스트레치 추가 (버튼들이 상단에 배치되도록)
        right_layout.addStretch()
        
        # 상태 표시줄 설정
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 프로그레스 바 (초기에는 숨김)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        self.status_bar.showMessage("준비됨")
    
    def _open_folder_dialog(self):
        """폴더 선택 다이얼로그 표시"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "폴더 선택",
            str(Path.home()),
            QFileDialog.ShowDirsOnly
        )
        
        if folder_path:
            self._load_folder(folder_path)
    
    def _load_folder(self, folder_path: str):
        """선택된 폴더 로드 및 트리 뷰 업데이트"""
        self.current_folder = Path(folder_path)
        logger.info(f"폴더 로드: {self.current_folder}")
        
        # 트리 모델 초기화
        self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels(["파일/폴더"])
        
        # 상태 표시 업데이트
        self.status_bar.showMessage(f"폴더 로드 중: {self.current_folder}")
        
        # 여기서 파일 시스템 스캔 호출 (구현 예정)
        # 지금은 임시 트리 노드만 추가
        root_item = QStandardItem(self.current_folder.name)
        self.tree_model.appendRow(root_item)
        
        # 임시 하위 항목 추가 (실제 구현에서는 스캔 결과로 대체)
        for i in range(3):
            child = QStandardItem(f"항목 {i+1}")
            root_item.appendRow(child)
        
        # 트리 확장
        self.tree_view.expand(self.tree_model.indexFromItem(root_item))
        
        # 상태 업데이트
        self.status_bar.showMessage(f"폴더 로드 완료: {self.current_folder}")
        self.token_label.setText("선택된 파일 없음")
        self.copy_btn.setEnabled(True) 