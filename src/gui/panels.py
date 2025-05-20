#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI 패널 위젯 모듈
애플리케이션의 좌측(파일 트리)과 우측(정보 및 액션) 패널 위젯을 정의합니다.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Set, Dict, Any

from PySide6.QtCore import Qt, Signal, Slot, QSize, QTimer, QModelIndex
from PySide6.QtGui import QStandardItemModel, QFont, QIcon, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QTreeView, QStyle, QApplication, QSplitter, QScrollArea
)

from .custom_widgets import CustomTreeView, CheckableItemDelegate
from src.gui.constants import ITEM_DATA_ROLE

logger = logging.getLogger(__name__)

class LeftPanelWidget(QWidget):
    """좌측 패널 위젯 (파일 트리)"""
    
    def __init__(self, parent=None, folder_icon=None, folder_open_icon=None):
        """
        좌측 패널 위젯 초기화
        
        Args:
            parent: 부모 위젯 (기본값: None)
            folder_icon: 폴더 아이콘 (기본값: None)
            folder_open_icon: 열린 폴더 아이콘 (기본값: None)
        """
        super().__init__(parent)
        self.setObjectName("leftPanel")
        logger.info("LeftPanelWidget 생성 시작")
        
        # 아이콘 저장 (폴더 아이콘만 보관)
        style = QApplication.style()
        self.folder_icon = folder_icon or style.standardIcon(QStyle.SP_DirIcon)
        self.folder_open_icon = folder_open_icon or style.standardIcon(QStyle.SP_DirOpenIcon)
        
        self._init_ui()
        
        # 트리 뷰 확장/축소 시그널 연결
        self.tree_view.expanded.connect(self.update_item_icon_on_expand)
        self.tree_view.collapsed.connect(self.update_item_icon_on_collapse)
        # 트리 뷰 항목 클릭 시그널 연결
        self.tree_view.item_clicked.connect(self._handle_file_item_clicked)
        
        logger.info("LeftPanelWidget 생성 완료")
    
    def _init_ui(self):
        """UI 구성요소 초기화"""
        # 좌측 패널 레이아웃
        left_panel_layout = QVBoxLayout(self)
        left_panel_layout.setContentsMargins(10, 10, 10, 10)
        
        # 크기 정책 설정 (수평/수직 확장)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 파일/폴더 헤더 라벨
        files_header = QLabel("Files/Folders")
        files_header.setObjectName("panelHeader")
        left_panel_layout.addWidget(files_header)
        
        # 트리 뷰 아이템 모델 생성 - 초기에는 빈 모델로 설정
        logger.info("트리 모델 초기화")
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Files/Folders"])
        
        # 파일 트리 뷰 - 커스텀 트리 뷰 사용
        logger.info("트리 뷰 초기화")
        self.tree_view = CustomTreeView()
        self.tree_view.setSelectionMode(QTreeView.NoSelection)
        self.tree_view.setAlternatingRowColors(False)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.header().setVisible(False)
        self.tree_view.setTextElideMode(Qt.ElideMiddle)
        self.tree_view.setAttribute(Qt.WA_MacShowFocusRect, False)  # macOS 포커스 사각형 제거
        self.tree_view.setFocusPolicy(Qt.NoFocus)  # 포커스 효과 제거
        self.tree_view.setMouseTracking(True)  # 마우스 트래킹 활성화 (호버 효과)
        
        # 더블 클릭으로 편집 방지
        self.tree_view.setEditTriggers(QTreeView.NoEditTriggers)
        
        # 마우스 이벤트 전파 허용
        self.tree_view.setAttribute(Qt.WA_NoMousePropagation, False)
        
        # 트리 뷰 크기 정책 설정 (수평/수직 확장)
        self.tree_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 트리 모델을 뷰에 설정
        logger.info("트리 모델을 뷰에 설정")
        self.tree_view.setModel(self.tree_model)
        
        # 가시성 명시적 설정
        self.tree_view.setVisible(True)
        
        # 커스텀 델리게이트 설정 (체크박스 스타일링)
        logger.info("델리게이트 설정")
        self.checkable_delegate = CheckableItemDelegate()
        self.tree_view.setItemDelegate(self.checkable_delegate)
        
        # 트리 뷰를 레이아웃에 추가
        left_panel_layout.addWidget(self.tree_view)
        logger.info("트리 뷰 레이아웃에 추가 완료")
    
    def set_tree_model(self, model):
        """
        트리 모델 설정
        
        Args:
            model: 설정할 트리 모델
        """
        self.tree_model = model
        self.tree_view.setModel(model)
        logger.info("트리 모델 설정 완료")

    def update_item_icon(self, index, icon_type):
        """
        트리 항목의 아이콘 업데이트
        
        Args:
            index: 업데이트할 항목의 인덱스
            icon_type: 적용할 아이콘 타입 ('folder' 또는 'folder_open')
        """
        if not index.isValid():
            return
            
        # 트리 모델이 QStandardItemModel인지 확인
        if not isinstance(self.tree_model, QStandardItemModel):
            return
            
        item = self.tree_model.itemFromIndex(index)
        metadata = item.data(ITEM_DATA_ROLE) if item else None
        if item and isinstance(metadata, dict) and metadata.get('is_dir', False):  # 디렉토리 항목인 경우만
            # 아이콘 타입에 따라 내부에 저장된 아이콘 사용
            if icon_type == 'folder_open':
                item.setIcon(self.folder_open_icon)
            else:  # 'folder'
                item.setIcon(self.folder_icon)
    
    def get_tree_model(self):
        """
        트리 모델 반환
        
        Returns:
            트리 뷰의 모델 객체
        """
        return self.tree_model
    
    def get_tree_view(self):
        """
        트리 뷰 객체 반환
        
        Returns:
            트리 뷰 객체
        """
        return self.tree_view

    def update_item_icon_on_expand(self, index):
        """
        트리 항목 확장 시 아이콘 업데이트
        
        Args:
            index: 확장된 항목의 인덱스
        """
        self.update_item_icon(index, 'folder_open')
        
    def update_item_icon_on_collapse(self, index):
        """
        트리 항목 축소 시 아이콘 업데이트
        
        Args:
            index: 축소된 항목의 인덱스
        """
        self.update_item_icon(index, 'folder')

    @Slot(QModelIndex)
    def _handle_file_item_clicked(self, index):
        """
        파일 항목 클릭 처리
        아이콘/이름 클릭 시 체크박스 상태를 토글합니다.
        
        Args:
            index: 클릭된 아이템의 모델 인덱스
        """
        # 트리 모델이 QStandardItemModel인지 확인
        if not isinstance(self.tree_model, QStandardItemModel):
            return
            
        # 인덱스로부터 항목 가져오기
        item = self.tree_model.itemFromIndex(index)
        
        # 항목 유효성 및 체크 가능 여부 확인
        if not item or not item.isCheckable() or not item.isEnabled():
            return
            
        # 항목 메타데이터 확인
        metadata = item.data(ITEM_DATA_ROLE)
        
        # 파일 항목인 경우에만 체크 상태 토글 - 즉시 처리
        if isinstance(metadata, dict) and not metadata.get('is_dir', False):
            # 기존 연결 일시 해제 (중복 처리 방지)
            try:
                model_connections_count = self.tree_model.receivers(self.tree_model.itemChanged)
                temporarily_disconnect = model_connections_count > 0
            except:
                temporarily_disconnect = False
                
            # 체크 상태 토글 (UI는 즉시 반응)
            current_state = item.checkState()
            
            # 체크 상태 변경
            if current_state == Qt.Checked:
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)
                
            # 토큰 계산을 위한 시그널은 별도로 0ms 지연 실행
            QTimer.singleShot(0, lambda: None)


class RightPanelWidget(QWidget):
    """우측 패널 위젯 (정보 및 액션)"""
    
    def __init__(self, parent=None, folder_icon=None, copy_icon=None, clear_icon=None):
        """
        우측 패널 위젯 초기화
        
        Args:
            parent: 부모 위젯 (기본값: None)
            folder_icon: 폴더 아이콘 (기본값: None)
            copy_icon: 복사 아이콘 (기본값: None)
            clear_icon: 클리어 아이콘 (기본값: None)
        """
        super().__init__(parent)
        self.setObjectName("rightPanel")
        logger.info("RightPanelWidget 생성 시작")
        
        # 아이콘 설정
        self.folder_icon = folder_icon or QApplication.style().standardIcon(QStyle.SP_DirIcon)
        self.copy_icon = copy_icon or QApplication.style().standardIcon(QStyle.SP_FileIcon)
        self.clear_icon = clear_icon or QApplication.style().standardIcon(QStyle.SP_DialogCloseButton)
        self.settings_icon = QApplication.style().standardIcon(QStyle.SP_FileDialogDetailedView)
        
        self._init_ui()
        logger.info("RightPanelWidget 생성 완료")
    
    def _init_ui(self):
        """UI 구성요소 초기화"""
        logger.info("우측 패널 UI 초기화")
        right_panel_layout = QVBoxLayout(self)
        right_panel_layout.setContentsMargins(10, 10, 10, 10)
        
        # 크기 정책 설정 (고정 수평, 확장 수직)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # 폴더 선택 그룹
        folder_header = QLabel("Folder Selection")
        folder_header.setObjectName("panelHeader")
        right_panel_layout.addWidget(folder_header)
        
        # 폴더 열기 버튼 및 경로 레이아웃
        folder_group = QWidget()
        folder_layout = QVBoxLayout(folder_group)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(10)  # 요소 간 간격 추가
        
        # 폴더 열기 버튼
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.setObjectName("openFolderButton")
        self.open_folder_button.setIcon(self.folder_icon)
        # 버튼 크기 정책 설정 - 너비 채우기
        self.open_folder_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.open_folder_button.setMinimumHeight(40)  # 버튼 높이 증가
        folder_layout.addWidget(self.open_folder_button)
        
        # 현재 폴더 경로를 표시할 수평 레이아웃
        current_folder_hbox_layout = QHBoxLayout()
        current_folder_hbox_layout.setContentsMargins(0, 4, 0, 0)
        
        # 현재 폴더 경로 라벨
        folder_path_label = QLabel("Current folder:")
        folder_path_label.setProperty("infoLabel", True)
        folder_path_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        current_folder_hbox_layout.addWidget(folder_path_label)
        
        self.folder_path = QLabel("No folder selected")
        self.folder_path.setObjectName("pathLabel")
        self.folder_path.setWordWrap(True)
        self.folder_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # 경로 라벨 크기 정책 설정 (수평 확장)
        self.folder_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        current_folder_hbox_layout.addWidget(self.folder_path)
        
        # 수평 레이아웃을 수직 레이아웃에 추가
        folder_layout.addLayout(current_folder_hbox_layout)
        
        right_panel_layout.addWidget(folder_group)
        
        # 선택 정보 그룹
        info_header = QLabel("Selection Info")
        info_header.setObjectName("panelHeader")
        right_panel_layout.addWidget(info_header)
        
        # 정보 표시 컨테이너 개선
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(12)  # 정보 항목 간격 증가
        
        info_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # 선택된 파일 수
        file_count_group = QWidget()
        file_count_layout = QHBoxLayout(file_count_group)
        file_count_layout.setContentsMargins(0, 4, 0, 4)
        
        selected_files_label = QLabel("Selected files:")
        selected_files_label.setProperty("infoLabel", True)
        selected_files_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        file_count_layout.addWidget(selected_files_label)
        
        file_count_layout.addStretch(1)  # 값을 오른쪽 정렬하기 위한 스트레치 추가
        
        self.selected_files_count = QLabel("0")
        self.selected_files_count.setProperty("infoValue", True)
        self.selected_files_count.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)  # 최소 크기
        self.selected_files_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # 텍스트 오른쪽 정렬
        file_count_layout.addWidget(self.selected_files_count)
        
        info_layout.addWidget(file_count_group)
        
        # 총 토큰 수
        token_count_group = QWidget()
        token_count_layout = QHBoxLayout(token_count_group)
        token_count_layout.setContentsMargins(0, 4, 0, 4)
        
        total_tokens_label = QLabel("Total tokens:")
        total_tokens_label.setProperty("infoLabel", True)
        total_tokens_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        token_count_layout.addWidget(total_tokens_label)
        
        token_count_layout.addStretch(1)  # 값을 오른쪽 정렬하기 위한 스트레치 추가
        
        self.total_tokens_count = QLabel("0")
        self.total_tokens_count.setProperty("infoValue", True)
        self.total_tokens_count.setObjectName("total_tokens_count")
        self.total_tokens_count.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)  # 최소 크기
        self.total_tokens_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # 텍스트 오른쪽 정렬
        token_count_layout.addWidget(self.total_tokens_count)
        
        info_layout.addWidget(token_count_group)
        
        right_panel_layout.addWidget(info_container)
        
        # 액션 버튼 그룹
        action_header = QLabel("Actions")
        action_header.setObjectName("panelHeader")
        right_panel_layout.addWidget(action_header)
        
        # 액션 버튼 컨테이너
        action_container = QWidget()
        action_layout = QVBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)  # 버튼 간 간격 추가
        
        # 클립보드에 복사 버튼
        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.setObjectName("copyButton")
        # 복사 버튼을 위한 문서 아이콘 사용
        self.copy_button.setIcon(self.copy_icon)
        # 아이콘 설정
        self.copy_button.setIconSize(QSize(20, 20))
        self.copy_button.setLayoutDirection(Qt.LeftToRight)
        self.copy_button.setEnabled(False)  # 초기에 비활성화
        # 복사 버튼 크기 정책
        self.copy_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.copy_button.setMinimumHeight(44)
        action_layout.addWidget(self.copy_button)
        
        # 선택 지우기 버튼
        self.clear_button = QPushButton("Clear Selection")
        self.clear_button.setObjectName("clearButton")
        # 클리어 버튼을 위한 X 아이콘 사용
        self.clear_button.setIcon(self.clear_icon)
        self.clear_button.setIconSize(QSize(20, 20))
        self.clear_button.setLayoutDirection(Qt.LeftToRight)
        self.clear_button.setEnabled(False)  # 초기에 비활성화
        self.clear_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.clear_button.setMinimumHeight(44)
        action_layout.addWidget(self.clear_button)
        
        # 설정 버튼
        self.settings_button = QPushButton("Settings")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setIcon(self.settings_icon)
        self.settings_button.setIconSize(QSize(20, 20))
        self.settings_button.setLayoutDirection(Qt.LeftToRight)
        self.settings_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.settings_button.setMinimumHeight(44)
        action_layout.addWidget(self.settings_button)
        
        right_panel_layout.addWidget(action_container)
        
        # 여백 추가 (하단 여백)
        right_panel_layout.addStretch() 
        
    def update_folder_path(self, path_str):
        """
        폴더 경로 라벨 업데이트
        
        Args:
            path_str: 표시할 폴더 경로 문자열
        """
        self.folder_path.setText(path_str)
        
    def update_selection_info(self, file_count_str, token_count_str):
        """
        선택 정보 라벨 업데이트
        
        Args:
            file_count_str: 선택된 파일 수 문자열
            token_count_str: 총 토큰 수 문자열
        """
        self.selected_files_count.setText(file_count_str)
        self.total_tokens_count.setText(token_count_str)
        
    def set_buttons_enabled(self, copy_enabled, clear_enabled):
        """
        버튼 활성화 상태 설정
        
        Args:
            copy_enabled: 복사 버튼 활성화 여부
            clear_enabled: 클리어 버튼 활성화 여부
        """
        self.copy_button.setEnabled(copy_enabled)
        self.clear_button.setEnabled(clear_enabled) 