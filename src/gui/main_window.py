#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
메인 윈도우 모듈
애플리케이션의 주요 UI 구성 요소를 정의합니다.
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Union, Tuple
import threading
from queue import Queue
import time
from functools import partial
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QFileDialog, QTreeView, QStatusBar,
    QMessageBox, QProgressBar, QMenu, QMenuBar, QApplication,
    QStyle, QCheckBox, QSizePolicy, QDialog, QDialogButtonBox, QFormLayout,
    QLineEdit, QComboBox, QStyledItemDelegate, QProxyStyle
)
from PySide6.QtCore import Qt, QSize, QDir, Signal, Slot, QThread, QSortFilterProxyModel, QModelIndex, QEvent, QObject
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction, QFont, QDesktopServices

# 파일 스캐너 모듈 임포트
from src.core.file_scanner import scan_directory, is_binary_file, read_text_file
# 토큰화 모듈 임포트
from src.core.tokenizer import Tokenizer
# .gitignore 필터링 모듈 임포트
from src.core.filter import GitignoreFilter
# 출력 포맷팅 모듈 임포트
from src.core.output_formatter import generate_file_map, generate_file_contents, generate_full_output
# 클립보드 유틸리티 모듈 임포트
from src.utils.clipboard_utils import copy_to_clipboard
from src.utils.settings_manager import SettingsManager
from src.gui.settings_dialog import SettingsDialog
from src.core.sort_utils import sort_items  # 정렬 유틸리티 임포트

logger = logging.getLogger(__name__)

# 파일 확장자에 해당하는 프로그래밍 언어 식별자 매핑
FILE_EXTENSIONS_TO_LANGUAGE = {
    # C 계열
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.hpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.c++': 'cpp',
    
    # 웹 개발
    '.html': 'html',
    '.htm': 'html',
    '.xhtml': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.less': 'less',
    '.js': 'javascript',
    '.jsx': 'jsx',
    '.ts': 'typescript',
    '.tsx': 'tsx',
    
    # Python
    '.py': 'python',
    '.pyw': 'python',
    '.pyx': 'python',
    '.pxd': 'python',
    '.pyi': 'python',
    '.ipynb': 'jupyter',
    
    # Java & JVM 기반
    '.java': 'java',
    '.kt': 'kotlin',
    '.kts': 'kotlin',
    '.scala': 'scala',
    '.groovy': 'groovy',
    
    # C#, .NET
    '.cs': 'csharp',
    '.vb': 'vb',
    '.fs': 'fsharp',
    
    # Ruby & PHP
    '.rb': 'ruby',
    '.php': 'php',
    
    # 시스템 프로그래밍
    '.go': 'go',
    '.rs': 'rust',
    '.swift': 'swift',
    
    # 스크립트 언어
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'bash',
    '.ps1': 'powershell',
    '.bat': 'batch',
    '.cmd': 'batch',
    
    # 마크업 & 데이터
    '.md': 'markdown',
    '.markdown': 'markdown',
    '.json': 'json',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.xml': 'xml',
    '.toml': 'toml',
    '.ini': 'ini',
    '.cfg': 'ini',
    '.csv': 'csv',
    '.tsv': 'tsv',
    
    # 기타
    '.sql': 'sql',
    '.graphql': 'graphql',
    '.gql': 'graphql',
    '.tex': 'latex',
    '.dockerfile': 'dockerfile',
    '.gitignore': 'gitignore',
}

class HoverEventFilter(QObject):
    """
    모든 호버 관련 이벤트를 필터링하는 이벤트 필터
    """
    def eventFilter(self, watched, event):
        # 호버 관련 이벤트 차단
        if event.type() == QEvent.HoverEnter or event.type() == QEvent.HoverLeave or event.type() == QEvent.HoverMove:
            return True  # 이벤트 처리된 것으로 간주하고 전파 중지
        
        # 기타 이벤트는 정상 처리
        return super().eventFilter(watched, event)

class NoHoverDelegate(QStyledItemDelegate):
    """
    호버 효과를 제거하는 커스텀 항목 델리게이트
    """
    def paint(self, painter, option, index):
        # 호버 상태 플래그 제거
        if option.state & QStyle.State_MouseOver:
            option.state &= ~QStyle.State_MouseOver
        
        # 선택 상태 플래그 제거
        if option.state & QStyle.State_Selected:
            option.state &= ~QStyle.State_Selected
        
        # 포커스 상태 플래그 제거
        if option.state & QStyle.State_HasFocus:
            option.state &= ~QStyle.State_HasFocus
        
        # 기본 그리기 메서드 호출
        super().paint(painter, option, index)

class NoHoverStyle(QProxyStyle):
    """
    호버 효과를 모두 제거하는 프록시 스타일
    """
    def __init__(self, style=None):
        super().__init__(style)
        
    def drawPrimitive(self, element, option, painter, widget=None):
        """
        기본 요소 그리기를 재정의하여 호버 효과 제거
        """
        # 항목 호버 효과 제거
        if element == QStyle.PE_PanelItemViewItem:
            # 호버 상태 제거
            if option.state & QStyle.State_MouseOver:
                option.state &= ~QStyle.State_MouseOver
            
            # 선택 상태 제거
            if option.state & QStyle.State_Selected:
                option.state &= ~QStyle.State_Selected
                
            # 포커스 상태 제거
            if option.state & QStyle.State_HasFocus:
                option.state &= ~QStyle.State_HasFocus
        
        # 상위 클래스의 그리기 메서드 호출
        super().drawPrimitive(element, option, painter, widget)
        
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        """
        스타일 힌트 재정의 - 호버 효과와 관련된 힌트 처리
        """
        # 호버 관련 힌트 비활성화
        if hint in [QStyle.SH_ItemView_ChangeHighlightOnFocus, QStyle.SH_ItemView_ShowDecorationSelected]:
            return 0
        
        # 그 외 힌트는 기본 처리
        return super().styleHint(hint, option, widget, returnData)

class TokenizerThread(QThread):
    """
    백그라운드 토큰 계산 스레드
    """
    # 시그널 정의
    progress_updated = Signal(int, int)  # 현재 진행 상태, 총 파일 수
    token_calculated = Signal(str, int)  # 파일 경로, 토큰 수
    calculation_finished = Signal()      # 계산 완료 시그널
    calculation_error = Signal(str)      # 오류 발생 시 메시지
    
    def __init__(self, files: List[Path], tokenizer: Tokenizer):
        """
        토큰화 스레드 초기화
        
        Args:
            files: 토큰 수를 계산할 파일 경로 목록
            tokenizer: 토큰화 객체
        """
        super().__init__()
        self.files = files
        self.tokenizer = tokenizer
        self.stopped = False
    
    def stop(self):
        """스레드 중지 요청"""
        self.stopped = True
    
    def run(self):
        """
        백그라운드에서 파일 목록의 토큰 수를 계산
        """
        try:
            total_files = len(self.files)
            for i, file_path in enumerate(self.files):
                # 종료 요청 확인
                if self.stopped:
                    break
                
                # 진행 상황 업데이트
                self.progress_updated.emit(i + 1, total_files)
                
                # 바이너리 파일은 건너뜀
                if is_binary_file(file_path):
                    self.token_calculated.emit(str(file_path), 0)
                    continue
                
                # 파일 내용 읽기
                content = read_text_file(file_path)
                
                # 오류 정보가 포함된 딕셔너리인 경우 건너뜀
                if isinstance(content, dict) and 'error' in content:
                    self.token_calculated.emit(str(file_path), 0)
                    continue
                
                # 토큰 수 계산
                token_count = self.tokenizer.count_tokens(content)
                
                # 결과 전송
                self.token_calculated.emit(str(file_path), token_count)
            
            # 계산 완료
            self.calculation_finished.emit()
        except Exception as e:
            logger.error(f"토큰 계산 중 오류: {e}")
            self.calculation_error.emit(str(e))

class MainWindow(QMainWindow):
    """메인 애플리케이션 윈도우"""
    
    def __init__(self):
        """메인 윈도우 초기화"""
        super().__init__()
        
        # 아이콘 초기화
        self._init_icons()
        
        # 설정 관리자 초기화
        self.settings_manager = SettingsManager()
        
        # 커스텀 호버 없는 스타일 적용
        self.custom_style = NoHoverStyle()
        
        # 기본 UI 설정
        self.setWindowTitle("LLM 프롬프트 헬퍼")
        self.setMinimumSize(800, 600)
        
        # 중앙 위젯 및 레이아웃 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 진행 표시줄 설정
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        
        # 토크나이저 초기화
        model_name = self.settings_manager.get_setting("model_name", "gpt-3.5-turbo")
        self.tokenizer = Tokenizer(model_name)
        
        # 트리 뷰 모델 설정
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(['파일/폴더'])
        
        # 체크된 아이템 추적
        self.checked_items = set()
        self.checked_files = 0
        self.checked_dirs = 0
        
        # 아이템 경로-객체 매핑
        self.item_path_map = {}
        
        # 토큰 계산 관련 변수
        self.token_cache = {}  # 파일 경로 -> 토큰 수 매핑
        self.total_tokens = 0
        self.file_cache = {}   # 파일 경로 -> 파일 내용 매핑
        
        # 현재 로드된 폴더
        self.current_folder = None
        
        # .gitignore 필터
        self.gitignore_filter = None
        
        # 토큰화 스레드 초기화
        self.token_thread = None
        
        # UI 초기화
        self._init_ui()
        
        # 메뉴 생성
        self._create_menu()
        
        # 기본 상태 메시지 설정
        self.statusBar().showMessage("폴더를 선택하세요.", 5000)
        
        logger.info("메인 윈도우 초기화 완료")
    
    def _init_icons(self):
        """아이콘 리소스 초기화"""
        # 커스텀 SVG 아이콘 사용
        self.folder_icon = QIcon(":/icons/folder.svg")
        self.folder_open_icon = QIcon(":/icons/folder_open.svg")
        self.file_icon = QIcon(":/icons/file_document.svg")
        self.code_file_icon = QIcon(":/icons/file_code.svg")
        self.doc_file_icon = QIcon(":/icons/file_document.svg")
        
        # 일부 특별한 아이콘은 시스템 아이콘 유지
        style = self.style()
        self.symlink_icon = style.standardIcon(QStyle.SP_FileLinkIcon)
        self.binary_icon = style.standardIcon(QStyle.SP_DriveHDIcon)
        self.error_icon = style.standardIcon(QStyle.SP_MessageBoxCritical)
        self.image_file_icon = style.standardIcon(QStyle.SP_DirLinkIcon)
        
        # 자주 사용되는 파일 확장자별 아이콘 매핑
        self.extension_icon_map = {
            # 코드 파일
            '.py': self.code_file_icon,
            '.js': self.code_file_icon,
            '.ts': self.code_file_icon,
            '.html': self.code_file_icon,
            '.css': self.code_file_icon,
            '.cpp': self.code_file_icon,
            '.c': self.code_file_icon,
            '.h': self.code_file_icon,
            '.java': self.code_file_icon,
            '.php': self.code_file_icon,
            '.rb': self.code_file_icon,
            '.go': self.code_file_icon,
            '.rs': self.code_file_icon,
            '.swift': self.code_file_icon,
            
            # 문서 파일
            '.txt': self.doc_file_icon,
            '.md': self.doc_file_icon,
            '.pdf': self.doc_file_icon,
            '.doc': self.doc_file_icon,
            '.docx': self.doc_file_icon,
            '.xls': self.doc_file_icon,
            '.xlsx': self.doc_file_icon,
            '.ppt': self.doc_file_icon,
            '.pptx': self.doc_file_icon,
            
            # 이미지 파일은 바이너리지만 특별 아이콘 적용
            '.jpg': self.image_file_icon,
            '.jpeg': self.image_file_icon,
            '.png': self.image_file_icon,
            '.gif': self.image_file_icon,
            '.svg': self.image_file_icon,
            '.ico': self.image_file_icon,
            '.bmp': self.image_file_icon,
        }
        
        logger.debug("아이콘 리소스 초기화 완료")
    
    def _init_ui(self):
        """
        UI 구성 요소 초기화
        """
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃 (수직)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)  # 레이아웃 요소 간 간격
        
        # 좌우 패널 스플리터 생성
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)  # 스플리터 핸들 너비 설정
        splitter.setChildrenCollapsible(False)  # 자식 위젯이 완전히 축소되지 않도록 설정
        
        # ===== 좌측 패널 (파일 트리 뷰) =====
        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(8, 8, 8, 8)
        
        # 크기 정책 설정 (수평/수직 확장)
        left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 파일/폴더 헤더 레이블
        files_header = QLabel("파일/폴더")
        files_header.setObjectName("panelHeader")
        left_panel_layout.addWidget(files_header)
        
        # 파일 트리 뷰
        self.tree_view = QTreeView()
        self.tree_view.setSelectionMode(QTreeView.NoSelection)
        self.tree_view.setAlternatingRowColors(False)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.header().setVisible(False)
        self.tree_view.setTextElideMode(Qt.ElideMiddle)
        self.tree_view.setAttribute(Qt.WA_MacShowFocusRect, False)  # macOS 포커스 사각형 제거
        self.tree_view.setFocusPolicy(Qt.NoFocus)  # 포커스 효과 제거
        self.tree_view.setMouseTracking(False)  # 마우스 추적 비활성화
        
        # 호버 이벤트 완전 필터링을 위한 이벤트 필터 설치
        hover_filter = HoverEventFilter(self.tree_view)
        self.tree_view.viewport().installEventFilter(hover_filter)
        self.tree_view.installEventFilter(hover_filter)
        
        # 호버 효과 제거를 위한 커스텀 델리게이트 설정
        no_hover_delegate = NoHoverDelegate(self.tree_view)
        self.tree_view.setItemDelegate(no_hover_delegate)
        
        # 호버 효과를 완전히 비활성화하기 위한 속성 설정
        self.tree_view.setAttribute(Qt.WA_NoMousePropagation, True)  # 마우스 이벤트 전파 차단
        
        # 직접 인라인 스타일 적용 (외부 스타일시트와 함께 적용)
        inline_style = """
            QTreeView::item:hover { 
                background-color: transparent !important; 
                border: none !important;
                color: #DCE0E8;
            }
            QTreeView::branch:hover { 
                background-color: transparent !important; 
                border: none !important;
            }
            QTreeView::indicator:hover {
                background-color: #282C34;
            }
        """
        self.tree_view.setStyleSheet(inline_style)
        
        # 커스텀 스타일 적용
        self.tree_view.setStyle(self.custom_style)
        
        # 트리 뷰의 크기 정책 설정 (수평/수직 확장)
        self.tree_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 트리 뷰 아이템 모델 생성
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["파일/폴더"])
        self.tree_view.setModel(self.tree_model)
        
        # 트리 뷰 이벤트 연결
        self.tree_model.itemChanged.connect(self._on_item_changed)
        
        # 폴더 확장/축소 이벤트 연결
        self.tree_view.expanded.connect(self._on_item_expanded)
        self.tree_view.collapsed.connect(self._on_item_collapsed)
        
        left_panel_layout.addWidget(self.tree_view)
        
        # 필터 옵션 컨테이너
        filter_container = QWidget()
        filter_layout = QVBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 8, 0, 0)
        
        # 필터 옵션 헤더 레이블
        filter_header = QLabel("필터 옵션")
        filter_header.setProperty("groupHeader", True)
        filter_layout.addWidget(filter_header)
        
        # 숨김 파일/폴더 표시 체크박스
        self.show_hidden_files_cb = QCheckBox("숨김 파일/폴더 표시")
        self.show_hidden_files_cb.setChecked(False)
        self.show_hidden_files_cb.stateChanged.connect(self._toggle_hidden_files)
        filter_layout.addWidget(self.show_hidden_files_cb)
        
        # .gitignore 규칙 적용 체크박스
        self.apply_gitignore_cb = QCheckBox(".gitignore 규칙 적용")
        self.apply_gitignore_cb.setChecked(True)
        self.apply_gitignore_cb.stateChanged.connect(self._toggle_gitignore_filter)
        filter_layout.addWidget(self.apply_gitignore_cb)
        
        left_panel_layout.addWidget(filter_container)
        
        # ===== 우측 패널 (정보 및 액션) =====
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(8, 8, 8, 8)
        
        # 크기 정책 설정 (수평 고정, 수직 확장)
        right_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # 폴더 선택 그룹
        folder_header = QLabel("폴더 선택")
        folder_header.setObjectName("panelHeader")
        right_panel_layout.addWidget(folder_header)
        
        # 폴더 열기 버튼 및 경로 표시
        folder_group = QWidget()
        folder_layout = QVBoxLayout(folder_group)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        
        # 폴더 열기 버튼
        self.open_folder_button = QPushButton("폴더 열기")
        self.open_folder_button.setObjectName("openFolderButton")
        self.open_folder_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.open_folder_button.clicked.connect(self._open_folder_dialog)
        folder_layout.addWidget(self.open_folder_button)
        
        # 현재 폴더 경로 레이블
        folder_path_label = QLabel("현재 폴더:")
        folder_path_label.setProperty("infoLabel", True)
        folder_layout.addWidget(folder_path_label)
        
        self.folder_path = QLabel("선택된 폴더 없음")
        self.folder_path.setObjectName("pathLabel")
        self.folder_path.setWordWrap(True)
        self.folder_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # 경로 레이블 크기 정책 설정 (수평 확장)
        self.folder_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        folder_layout.addWidget(self.folder_path)
        
        right_panel_layout.addWidget(folder_group)
        
        # 선택 정보 그룹
        info_header = QLabel("선택 정보")
        info_header.setObjectName("panelHeader")
        right_panel_layout.addWidget(info_header)
        
        # 정보 표시 컨테이너 개선
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)  # 정보 항목 간 간격 설정
        
        info_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # 선택된 파일 수
        file_count_group = QWidget()
        file_count_layout = QHBoxLayout(file_count_group)
        file_count_layout.setContentsMargins(0, 4, 0, 4)
        
        selected_files_label = QLabel("선택된 파일:")
        selected_files_label.setProperty("infoLabel", True)
        selected_files_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        file_count_layout.addWidget(selected_files_label)
        
        self.selected_files_count = QLabel("0개")
        self.selected_files_count.setProperty("infoValue", True)
        self.selected_files_count.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        file_count_layout.addWidget(self.selected_files_count)
        file_count_layout.addStretch()
        
        info_layout.addWidget(file_count_group)
        
        # 총 토큰 수
        token_count_group = QWidget()
        token_count_layout = QHBoxLayout(token_count_group)
        token_count_layout.setContentsMargins(0, 4, 0, 4)
        
        total_tokens_label = QLabel("총 토큰 수:")
        total_tokens_label.setProperty("infoLabel", True)
        token_count_layout.addWidget(total_tokens_label)
        
        self.total_tokens_count = QLabel("0")
        self.total_tokens_count.setProperty("infoValue", True)
        self.total_tokens_count.setObjectName("counterLabel")
        token_count_layout.addWidget(self.total_tokens_count)
        token_count_layout.addStretch()
        
        info_layout.addWidget(token_count_group)
        
        # 현재 모델 정보
        model_group = QWidget()
        model_layout = QHBoxLayout(model_group)
        model_layout.setContentsMargins(0, 4, 0, 4)
        
        model_label = QLabel("현재 모델:")
        model_label.setProperty("infoLabel", True)
        model_layout.addWidget(model_label)
        
        self.model_name = QLabel(self.tokenizer.model_name)
        self.model_name.setProperty("infoValue", True)
        model_layout.addWidget(self.model_name)
        model_layout.addStretch()
        
        info_layout.addWidget(model_group)
        
        right_panel_layout.addWidget(info_container)
        
        # 작업 버튼 그룹
        action_header = QLabel("작업")
        action_header.setObjectName("panelHeader")
        right_panel_layout.addWidget(action_header)
        
        # 작업 버튼 컨테이너
        action_container = QWidget()
        action_layout = QVBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        
        # 클립보드에 복사 버튼
        self.copy_button = QPushButton("클립보드에 복사")
        self.copy_button.setObjectName("copyButton")
        self.copy_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.copy_button.clicked.connect(self._copy_to_clipboard)
        self.copy_button.setEnabled(False)  # 초기에는 비활성화
        # 복사 버튼 크기 정책 설정 (수평 확장)
        self.copy_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.copy_button.setMinimumHeight(40)  # 버튼 높이 설정
        action_layout.addWidget(self.copy_button)
        
        # 설정 열기 버튼
        self.settings_button = QPushButton("설정")
        self.settings_button.setProperty("secondary", True)
        self.settings_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.settings_button.clicked.connect(self._show_settings_dialog)
        action_layout.addWidget(self.settings_button)
        
        right_panel_layout.addWidget(action_container)
        
        # 여백 추가 (하단 여백)
        right_panel_layout.addStretch()
        
        # 패널을 스플리터에 추가
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # 창 최소 크기 설정 (더 여유 있게)
        self.setMinimumSize(900, 650)
        
        # 스플리터 초기 크기 비율 설정 (좌:우 = 7:3)
        splitter.setSizes([700, 300])
        
        # 스플리터 크기 정책 설정
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 메인 레이아웃에 스플리터 추가
        main_layout.addWidget(splitter)
        
        # 상태 표시줄 생성
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # 상태 메시지 레이블
        self.status_label = QLabel("준비")
        status_bar.addWidget(self.status_label, 1)
        
        # 프로그레스 바 추가
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        status_bar.addPermanentWidget(self.progress_bar)
        
        # 메뉴바 생성
        self._create_menu()
        
        # 윈도우 크기 및 제목 설정
        self.setWindowTitle("LLM 프롬프트 헬퍼")
        self.resize(1200, 800)  # 초기 윈도우 크기 (좀 더 넓게)
        
        # 윈도우 아이콘 설정
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_FileDialogInfoView))
        
        # 상태 표시줄 초기 메시지
        self.statusBar().showMessage("준비됨", 3000)
        
        # 중앙에 윈도우 배치
        self._center_window()
        
        # UI 초기화 완료 로그
        logger.info("UI 초기화 완료")
        
        # 스타일시트를 통해 사용자 정의 스타일 적용
        # (resources.py에 컴파일된 QSS 파일 사용)
        
        # 주의: QTreeView에는 setTristate 메소드가 없음
        # 부분 체크 상태는 _on_item_changed 및 _update_parent_checked_state 메소드에서 수동으로 처리
    
    def _create_menu(self):
        """메뉴 바 생성"""
        menubar = QMenuBar()
        self.setMenuBar(menubar)
        
        # 파일 메뉴
        file_menu = QMenu("파일", self)
        menubar.addMenu(file_menu)
        
        # 폴더 열기 액션
        open_folder_action = QAction("폴더 열기", self)
        open_folder_action.setShortcut("Ctrl+O")
        open_folder_action.triggered.connect(self._open_folder_dialog)
        file_menu.addAction(open_folder_action)
        
        file_menu.addSeparator()
        
        # 설정 액션
        settings_action = QAction("설정", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._show_settings_dialog)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # 종료 액션
        exit_action = QAction("종료", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 도움말 메뉴
        help_menu = QMenu("도움말", self)
        menubar.addMenu(help_menu)
        
        # 정보 액션
        about_action = QAction("정보", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)
    
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
        """
        지정된 폴더 경로를 로드하여 트리 뷰에 표시
        
        Args:
            folder_path: 로드할 폴더 경로
        """
        try:
            self.current_folder = Path(folder_path)
            
            # 기존 토큰화 스레드가 있으면 중지
            if self.token_thread and self.token_thread.isRunning():
                self.token_thread.stop()
                self.token_thread.wait()
            
            # 상태 초기화
            self.checked_items.clear()
            self.checked_files = 0
            self.checked_dirs = 0
            self.total_tokens = 0
            self.token_cache.clear()
            self.file_cache.clear()
            
            # UI 업데이트
            self.folder_path.setText(folder_path)
            self.selected_files_count.setText("0개")
            self.total_tokens_count.setText("0")
            self.copy_button.setEnabled(False)
            
            # .gitignore 필터 초기화
            apply_gitignore = self.apply_gitignore_cb.isChecked()
            if apply_gitignore:
                self.gitignore_filter = GitignoreFilter(folder_path)
                if self.gitignore_filter.has_gitignore():
                    self.statusBar().showMessage(f".gitignore 규칙을 적용합니다: {self.gitignore_filter.get_gitignore_path()}", 5000)
                else:
                    self.statusBar().showMessage(".gitignore 파일이 없습니다. 필터링 없이 모든 파일이 표시됩니다.", 5000)
                    self.gitignore_filter = None
            else:
                self.gitignore_filter = None
                
            # 파일 및 폴더 스캔
            include_hidden = self.show_hidden_files_cb.isChecked()
            items = scan_directory(folder_path, follow_symlinks=False, include_hidden=include_hidden)
            
            # .gitignore 필터링 적용
            if self.gitignore_filter and apply_gitignore:
                filtered_items = []
                ignored_count = 0
                
                for item in items:
                    path = item['path']
                    # 루트 디렉토리 자체는 항상 포함
                    if path == self.current_folder:
                        filtered_items.append(item)
                        continue
                        
                    # .gitignore 규칙 적용
                    if self.gitignore_filter.should_ignore(path):
                        ignored_count += 1
                        continue
                    
                    filtered_items.append(item)
                
                items = filtered_items
                
                if ignored_count > 0:
                    self.statusBar().showMessage(f"{ignored_count}개 항목이 .gitignore 규칙으로 필터링되었습니다.", 5000)
            
            # venv 폴더 필터링 추가
            venv_count = 0
            filtered_items = []
            
            for item in items:
                path = item['path']
                rel_path = item.get('rel_path', '')
                parts = Path(rel_path).parts
                
                # 루트 디렉토리 자체는 항상 포함
                if path == self.current_folder:
                    filtered_items.append(item)
                    continue
                
                # venv, virtualenv, env 등의 가상환경 폴더 제외
                is_venv = False
                for part in parts:
                    if part in ['venv', 'virtualenv', 'env', '.venv'] or part.startswith('venv-'):
                        is_venv = True
                        venv_count += 1
                        break
                
                if not is_venv:
                    filtered_items.append(item)
            
            items = filtered_items
            
            if venv_count > 0:
                self.statusBar().showMessage(f"{venv_count}개 가상환경 폴더가 필터링되었습니다.", 5000)
            
            # 정렬 적용 - 전체 항목 목록을 먼저 정렬
            items = sort_items(items)
            logger.info(f"정렬 완료: 폴더 우선, 이름순으로 {len(items)}개 항목 정렬됨")
            
            # 트리 뷰 모델 초기화 및 채우기
            self.tree_model.clear()
            self.tree_model.setHorizontalHeaderLabels(['파일/폴더'])
            
            # 트리 뷰에 항목 추가
            self._populate_tree_view(items)
            
            # 모든 파일 경로를 리스트로 수집
            text_files = []
            for item in items:
                path = item.get('path')
                is_dir = item.get('is_dir')
                error = item.get('error')
                
                # 디렉토리나 오류가 있는 항목은 제외
                if is_dir or error:
                    continue
                
                # 텍스트 파일만 추가
                if not is_binary_file(path):
                    text_files.append(path)
            
            # 백그라운드에서 토큰 계산 시작
            self._start_token_calculation(text_files)
            
            logger.info(f"폴더 로드 완료: {folder_path}")
            
        except Exception as e:
            logger.error(f"폴더 로드 중 오류: {e}")
            self.statusBar().showMessage(f"오류: {str(e)}", 5000)
    
    def _populate_tree_view(self, items: List[Dict[str, Any]]):
        """
        파일 및 폴더 목록으로 트리 뷰 채우기
        
        Args:
            items: 파일 및 폴더 정보 목록 (이미 정렬된 상태여야 함)
        """
        # 아이템 사전 (경로를 키로 사용)
        item_dict = {}
        
        # 루트 아이템 생성
        root_item = None
        root_rel_path = Path('.')
        
        # 먼저 루트 디렉토리 아이템 찾기
        for i, info in enumerate(items):
            rel_path = info.get('rel_path')
            if rel_path == root_rel_path:
                root_item = QStandardItem(self.current_folder.name)
                root_item.setIcon(self.folder_icon)
                root_item.setCheckable(True)
                root_item.setData(True, Qt.UserRole)  # 디렉토리 플래그 추가
                item_dict[rel_path] = root_item
                self.tree_model.appendRow(root_item)
                break
        
        if not root_item:
            # 루트 아이템이 없으면 생성
            root_item = QStandardItem(self.current_folder.name)
            root_item.setIcon(self.folder_icon)
            root_item.setCheckable(True)
            root_item.setData(True, Qt.UserRole)  # 디렉토리 플래그 추가
            item_dict[root_rel_path] = root_item
            self.tree_model.appendRow(root_item)
        
        # 나머지 항목 처리 (루트 제외)
        for info in items:
            rel_path = info.get('rel_path')
            
            # 루트 아이템은 이미 처리함
            if rel_path == root_rel_path:
                continue
            
            path = info.get('path')
            is_dir = info.get('is_dir')
            is_symlink = info.get('is_symlink')
            is_hidden = info.get('is_hidden')
            error = info.get('error')
            
            # 상대 경로의 부모 경로 구하기
            parent_path = rel_path.parent
            
            # 부모 아이템 찾기
            parent_item = item_dict.get(parent_path)
            if not parent_item:
                # 필요한 부모 경로가 없는 경우 (필터링 등으로 인해),
                # 중간 경로를 생성해야 함
                current_parent_path = Path('.')
                current_parent_item = root_item
                
                # 부모 경로 분해
                path_parts = list(parent_path.parts)
                
                for part in path_parts:
                    current_parent_path = current_parent_path / part
                    if current_parent_path in item_dict:
                        current_parent_item = item_dict[current_parent_path]
                    else:
                        # 중간 경로 노드 생성
                        new_parent_item = QStandardItem(part)
                        new_parent_item.setIcon(self.folder_icon)
                        new_parent_item.setCheckable(True)
                        new_parent_item.setData(True, Qt.UserRole)  # 디렉토리 플래그 추가
                        current_parent_item.appendRow(new_parent_item)
                        item_dict[current_parent_path] = new_parent_item
                        current_parent_item = new_parent_item
                
                parent_item = current_parent_item
            
            # 현재 아이템 이름
            name = path.name
            
            # 아이템 생성
            item = QStandardItem(name)
            
            # 기본 정보 수집 (툴큅용)
            file_info = []
            file_info.append(f"경로: {path}")
            
            # 파일 크기 정보 추가 (파일인 경우)
            if not is_dir and path.exists():
                try:
                    size_bytes = path.stat().st_size
                    # 파일 크기를 적절한 단위로 변환
                    if size_bytes < 1024:
                        size_str = f"{size_bytes} 바이트"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes/1024:.1f} KB"
                    elif size_bytes < 1024 * 1024 * 1024:
                        size_str = f"{size_bytes/(1024*1024):.1f} MB"
                    else:
                        size_str = f"{size_bytes/(1024*1024*1024):.2f} GB"
                    file_info.append(f"크기: {size_str}")
                except:
                    pass
            
            # 오류 항목 처리
            if error:
                item.setIcon(self.error_icon)
                item.setForeground(Qt.red)
                
                if error == 'access_denied':
                    file_info.append("오류: 접근 권한 없음")
                else:
                    file_info.append(f"오류: {error}")
                    
                item.setToolTip("\n".join(file_info))
                parent_item.appendRow(item)
                item_dict[rel_path] = item
                continue
            
            # 심볼릭 링크 처리
            if is_symlink:
                item.setIcon(self.symlink_icon)
                try:
                    target = os.readlink(path)
                    file_info.append(f"심볼릭 링크 -> {target}")
                except OSError as e:
                    file_info.append(f"심볼릭 링크 (대상 읽기 오류: {e})")
            
            # 디렉토리 처리
            if is_dir:
                if not is_symlink:
                    item.setIcon(self.folder_icon)
                
                try:
                    # 항목 수 계산 (권한 오류 가능성 있음)
                    item_count = sum(1 for _ in path.iterdir())
                    file_info.append(f"항목 수: {item_count}")
                except PermissionError:
                    file_info.append("권한 오류: 내용을 읽을 수 없음")
                except Exception as e:
                    file_info.append(f"오류: {e}")
                
                item.setToolTip("\n".join(file_info))
                
                # 폴더 체크박스 추가
                item.setCheckable(True)
                item.setData(True, Qt.UserRole)  # 디렉토리 플래그 추가
                
                # 숨김 폴더 처리
                if is_hidden:
                    item.setForeground(Qt.gray)
                    file_info.append("숨김 폴더")
                    item.setToolTip("\n".join(file_info))
            
            # 일반 파일 처리
            else:
                # 바이너리 파일인지 확인
                is_binary = is_binary_file(path)
                
                if is_binary:
                    item.setIcon(self.binary_icon)
                    item.setForeground(Qt.gray)
                    file_info.append("바이너리 파일 (토큰 계산에서 제외됨)")
                    item.setToolTip("\n".join(file_info))
                    item.setData(True, Qt.UserRole + 1)  # 바이너리 파일 플래그
                    item.setData(False, Qt.UserRole)  # 디렉토리 아님 플래그
                else:
                    # 확장자별 아이콘 설정
                    ext = path.suffix.lower()
                    if ext in self.extension_icon_map:
                        item.setIcon(self.extension_icon_map[ext])
                        # 언어 정보 추가
                        language = FILE_EXTENSIONS_TO_LANGUAGE.get(ext)
                        if language:
                            file_info.append(f"언어: {language}")
                    else:
                        item.setIcon(self.file_icon)
                    
                    file_info.append("텍스트 파일")
                    
                    # 마지막 수정 시간 추가
                    try:
                        mod_time = datetime.fromtimestamp(path.stat().st_mtime)
                        file_info.append(f"수정일: {mod_time.strftime('%Y-%m-%d %H:%M')}")
                    except:
                        pass
                    
                    item.setToolTip("\n".join(file_info))
                    item.setData(False, Qt.UserRole + 1)  # 바이너리 파일 아님
                    item.setData(False, Qt.UserRole)  # 디렉토리 아님 플래그
                
                # 숨김 파일 표시
                if is_hidden:
                    if not is_binary:  # 이미 회색이 아닌 경우에만 변경
                        item.setForeground(Qt.gray)
                    file_info.append("숨김 파일")
                    item.setToolTip("\n".join(file_info))
                
                # 체크박스 추가 (모든 파일에 체크박스 추가)
                item.setCheckable(True)
                
                # .gitignore에 의해 무시되지만 표시된 항목의 경우 시각적으로 구분
                if self.gitignore_filter and self.gitignore_filter.should_ignore(path):
                    # 회색의 더 밝은 색조로 표시
                    item.setForeground(Qt.lightGray)
                    file_info.append(".gitignore 규칙에 의해 무시됨")
                    item.setToolTip("\n".join(file_info))
                    # 체크박스 비활성화 (선택 불가)
                    item.setEnabled(False)
            
            parent_item.appendRow(item)
            item_dict[rel_path] = item
        
        # 트리 전체 펼치기 제거 - 모든 폴더가 닫힌 상태로 시작하도록 함
        # self.tree_view.expandAll()
        
        # 루트 아이템만 펼치기 (첫 번째 레벨은 보이도록)
        self.tree_view.expand(self.tree_model.index(0, 0))
        
        # 파일 열 너비 자동 조정
        self.tree_view.resizeColumnToContents(0)
        
        logger.info(f"트리 뷰 채우기 완료: {len(items)}개 항목")
    
    def _on_item_changed(self, item):
        """
        트리 아이템 변경 시 호출되는 슬롯
        체크박스 상태 변경 시 토큰 계산 로직 처리 및 부모/자식 자동 선택/해제
        
        Args:
            item: 변경된 아이템
        """
        if not self.current_folder:
            return
            
        # 체크 상태가 변경된 경우에만 처리
        if item.isCheckable():
            checked = item.checkState() == Qt.Checked
            item_path = self._get_item_path(item)
            
            if not item_path:
                return

            # 상태 변경 이벤트 캐치로 인한 재귀 호출을 막기 위해 모델 시그널 연결 해제
            self.tree_model.itemChanged.disconnect(self._on_item_changed)
            
            try:
                # 체크 상태에 따라 처리
                is_dir = item_path.is_dir()
                
                # 이전 체크 상태를 기록
                was_checked = str(item_path) in self.checked_items
                
                # 현재 체크 상태로 처리
                if checked != was_checked:
                    if checked:
                        self.checked_items.add(str(item_path))
                        if is_dir:
                            self.checked_dirs += 1
                        else:
                            self.checked_files += 1
                        logger.debug(f"아이템 체크됨: {item_path}")
                    else:
                        self.checked_items.discard(str(item_path))
                        if is_dir:
                            self.checked_dirs -= 1
                        else:
                            self.checked_files -= 1
                
                # 폴더인 경우 하위 항목 상태도 함께 변경
                if is_dir:
                    logger.debug(f"디렉토리 체크 상태 변경: {item_path}, 체크됨: {checked}")
                    # 하위 항목 모두 동일한 체크 상태로 설정
                    self._set_item_checked_state(item, checked)
                
                # 부모 폴더의 체크 상태 업데이트
                self._update_parent_checked_state(item)
                
                # 총 토큰 수 업데이트
                self._update_token_count()
                
                # 선택된 파일 수 표시 업데이트
                self.selected_files_count.setText(f"{self.checked_files}개")
                
                # 복사 버튼 활성화 상태 업데이트
                self.copy_button.setEnabled(self.checked_files > 0)
            finally:
                # 모델 시그널 다시 연결
                self.tree_model.itemChanged.connect(self._on_item_changed)
    
    def _set_item_checked_state(self, item, checked):
        """
        아이템과 모든 자식 아이템의 체크 상태를 설정
        
        Args:
            item: 대상 아이템
            checked: 설정할 체크 상태 (True: 체크됨, False: 체크 해제됨)
        """
        # 현재 아이템의 체크 상태 설정
        check_state = Qt.Checked if checked else Qt.Unchecked
        item.setCheckState(check_state)
        
        # 아이템 경로 가져오기 (현재 아이템 상태를 tracked_items에 반영하기 위해)
        item_path = self._get_item_path(item)
        if item_path:
            is_dir = item_path.is_dir()
            path_str = str(item_path)
            
            # 이전 체크 상태
            was_checked = path_str in self.checked_items
            
            # 상태가 변경된 경우에만 처리
            if checked != was_checked:
                if checked:
                    self.checked_items.add(path_str)
                    if is_dir:
                        self.checked_dirs += 1
                    else:
                        self.checked_files += 1
                else:
                    self.checked_items.discard(path_str)
                    if is_dir:
                        self.checked_dirs -= 1
                    else:
                        self.checked_files -= 1
        
        # 모든 자식 아이템 처리
        row_count = item.rowCount()
        for row in range(row_count):
            child_item = item.child(row)
            if child_item and child_item.isCheckable():
                self._set_item_checked_state(child_item, checked)
    
    def _update_parent_checked_state(self, item):
        """
        부모 아이템의 체크 상태를 자식 아이템들의 상태를 기준으로 업데이트
        
        Args:
            item: 상태가 변경된 아이템
        """
        parent = item.parent()
        if not parent:
            return  # 루트 아이템이면 패스
        
        # 부모의 모든 자식 상태 확인
        all_checked = True
        any_checked = False
        
        row_count = parent.rowCount()
        for row in range(row_count):
            child = parent.child(row)
            if child and child.isCheckable():
                if child.checkState() == Qt.Checked:
                    any_checked = True
                else:
                    all_checked = False
                
                if any_checked and not all_checked:
                    break  # 상태 결정을 위한 충분한 정보 확보
        
        # 부모 상태 업데이트
        if all_checked:
            parent.setCheckState(Qt.Checked)
        elif any_checked:
            # 일부만 체크된 경우 부분 체크 상태로 설정
            parent.setCheckState(Qt.PartiallyChecked)
        else:
            parent.setCheckState(Qt.Unchecked)
        
        # 부모 경로 가져오기
        parent_path = self._get_item_path(parent)
        if parent_path:
            is_dir = parent_path.is_dir()
            path_str = str(parent_path)
            
            # 부모가 체크되었는지 여부 (완전히 체크된 경우만 카운트)
            is_checked = all_checked
            was_checked = path_str in self.checked_items
            
            # 상태가 변경된 경우에만 처리
            if is_checked != was_checked:
                if is_checked:
                    self.checked_items.add(path_str)
                    if is_dir:
                        self.checked_dirs += 1
                    else:
                        self.checked_files += 1
                else:
                    self.checked_items.discard(path_str)
                    if is_dir:
                        self.checked_dirs -= 1
                    else:
                        self.checked_files -= 1
        
        # 재귀적으로 상위 부모 상태도 업데이트
        self._update_parent_checked_state(parent)
    
    def _get_item_path(self, item):
        """
        트리 아이템의 전체 경로 반환
        
        Args:
            item: 트리 아이템
            
        Returns:
            Path 객체 또는 None
        """
        if not self.current_folder:
            return None
            
        # 아이템 경로 구성
        path_parts = []
        
        # 현재 아이템 이름
        path_parts.append(item.text())
        
        # 부모 아이템 경로 추가
        parent = item.parent()
        while parent:
            path_parts.append(parent.text())
            parent = parent.parent()
        
        # 역순으로 경로 구성 (루트->리프)
        path_parts.reverse()
        
        # 첫 번째 항목이 루트 폴더 이름이면 제외
        if path_parts and path_parts[0] == self.current_folder.name:
            path_parts = path_parts[1:]
        
        # 상대 경로 생성
        rel_path = Path(*path_parts)
        
        # 절대 경로 반환
        return self.current_folder / rel_path
    
    def _start_token_calculation(self, files: List[Path]):
        """
        백그라운드에서 토큰 계산 시작
        
        Args:
            files: 토큰을 계산할 파일 경로 목록
        """
        if not files:
            return
            
        # 프로그레스 바 초기화 및 표시
        self.progress_bar.setRange(0, len(files))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # 상태 메시지 업데이트
        self.statusBar().showMessage(f"토큰 계산 중... (0/{len(files)} 파일)")
        
        # 토큰화 스레드 생성 및 시작
        self.token_thread = TokenizerThread(files, self.tokenizer)
        
        # 시그널 연결
        self.token_thread.progress_updated.connect(self._on_token_progress)
        self.token_thread.token_calculated.connect(self._on_token_calculated)
        self.token_thread.calculation_finished.connect(self._on_token_calculation_finished)
        self.token_thread.calculation_error.connect(self._on_token_calculation_error)
        
        # 스레드 시작
        self.token_thread.start()
    
    def _on_token_progress(self, current: int, total: int):
        """
        토큰 계산 진행 상황 업데이트
        
        Args:
            current: 현재 처리 중인 파일 인덱스
            total: 총 파일 수
        """
        self.progress_bar.setValue(current)
        self.statusBar().showMessage(f"토큰 계산 중... ({current}/{total} 파일)")
    
    def _on_token_calculated(self, file_path: str, token_count: int):
        """
        파일의 토큰 계산 결과 처리
        
        Args:
            file_path: 파일 경로
            token_count: 계산된 토큰 수
        """
        # 토큰 캐시 업데이트
        self.token_cache[file_path] = token_count
        
        # 현재 체크된 항목이면 총 토큰 수에 추가
        if file_path in self.checked_items:
            self.total_tokens += token_count
            self.total_tokens_count.setText(f"{self.total_tokens:,}")
    
    def _on_token_calculation_finished(self):
        """토큰 계산 완료 시 호출"""
        # 프로그레스 바 숨기기
        self.progress_bar.setVisible(False)
        
        # 상태 메시지 업데이트
        total_files = len(self.token_cache)
        self.statusBar().showMessage(f"토큰 계산 완료 ({total_files} 파일)", 5000)
        
        # 토큰 수 업데이트
        self._update_token_count()
    
    def _on_token_calculation_error(self, error_msg: str):
        """
        토큰 계산 중 오류 발생 시 호출
        
        Args:
            error_msg: 오류 메시지
        """
        # 프로그레스 바 숨기기
        self.progress_bar.setVisible(False)
        
        # 오류 메시지 표시
        self.statusBar().showMessage(f"토큰 계산 중 오류: {error_msg}", 10000)
    
    def _update_token_count(self):
        """선택된 항목의 총 토큰 수 계산 및 UI 업데이트"""
        # 백그라운드 계산이 진행 중이면 중복 계산하지 않음
        if self.token_thread and self.token_thread.isRunning():
            return
            
        self.total_tokens = 0
        excluded_files = 0
        
        for path_str in self.checked_items:
            path = Path(path_str)
            
            # 디렉토리는 건너뜀
            if path.is_dir():
                continue
                
            # 트리 아이템 찾기 (UI에 표시된 정보 확인용)
            item = self._find_item_by_path(path)
            
            # 바이너리 파일이나 오류 상태인 파일은 건너뜀
            if item and item.data(Qt.UserRole + 1) == True:
                excluded_files += 1
                continue
            
            # 직접 바이너리 파일 확인 (UI 아이템을 찾지 못한 경우)
            if not item and is_binary_file(path):
                excluded_files += 1
                continue
                
            # 캐시된 토큰 수가 있으면 사용
            if path_str in self.token_cache:
                self.total_tokens += self.token_cache[path_str]
                continue
                
            # 백그라운드 계산 중이 아닌데 캐시에 없는 경우 계산
            # 파일 내용 읽기
            content = read_text_file(path)
            
            # 오류 정보가 포함된 딕셔너리인 경우 건너뜀
            if isinstance(content, dict) and 'error' in content:
                self.token_cache[path_str] = 0
                excluded_files += 1
                continue
                
            # 토큰 수 계산 및 캐싱
            token_count = self.tokenizer.count_tokens(content)
            self.token_cache[path_str] = token_count
            self.file_cache[path_str] = content
            self.total_tokens += token_count
        
        # UI 업데이트
        self.total_tokens_count.setText(f"{self.total_tokens:,}")
        self.selected_files_count.setText(f"{self.checked_files}개")
        
        # 제외된 파일이 있으면 상태 표시줄에 정보 표시
        if excluded_files > 0:
            self.statusBar().showMessage(f"{excluded_files}개 파일이 토큰 계산에서 제외됨 (바이너리 파일 또는 오류)", 5000)
        
        # 복사 버튼 활성화 상태 업데이트
        self.copy_button.setEnabled(self.checked_files > 0)
    
    def _find_item_by_path(self, path: Path) -> Optional[QStandardItem]:
        """
        경로에 해당하는 트리 아이템을 찾아 반환
        
        Args:
            path: 찾을 파일/폴더 경로
            
        Returns:
            찾은 QStandardItem 또는 None
        """
        if not self.current_folder:
            return None
            
        # 상대 경로 계산
        try:
            rel_path = path.relative_to(self.current_folder)
        except ValueError:
            return None
            
        # 루트부터 시작하여 경로 따라가기
        parent_item = self.tree_model.item(0)  # 루트 아이템
        if not parent_item:
            return None
            
        # 경로 파트가 없으면 루트 아이템 자체 반환
        if len(rel_path.parts) == 0:
            return parent_item
            
        # 각 경로 파트에 대해 자식 아이템 찾기
        for part in rel_path.parts:
            found = False
            for row in range(parent_item.rowCount()):
                child = parent_item.child(row)
                if child and child.text() == part:
                    parent_item = child
                    found = True
                    break
            
            if not found:
                return None
                
        return parent_item
    
    def _show_about_dialog(self):
        """정보 대화상자 표시"""
        try:
            msg_box = QMessageBox(self)
            msg_box.setObjectName("information")
            msg_box.setWindowTitle("프로그램 정보")
            msg_box.setText(
                "LLM 프롬프트 헬퍼 v1.0\n\n"
                "이 프로그램은 LLM(대규모 언어 모델)에 코드베이스 정보를 "
                "프롬프트로 전달할 때 유용한 형식으로 변환해주는 도구입니다.\n\n"
                "© 2023 LLM 프롬프트 헬퍼 프로젝트"
            )
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()
        except Exception as e:
            logger.error(f"정보 대화상자 표시 중 오류: {str(e)}")
    
    def _toggle_hidden_files(self):
        """숨김 파일/폴더 표시 토글"""
        if self.current_folder:
            self._load_folder(str(self.current_folder))
    
    def _toggle_gitignore_filter(self):
        """.gitignore 필터 적용 토글"""
        if self.current_folder:
            self._load_folder(str(self.current_folder))
    
    def _copy_to_clipboard(self):
        """
        선택된 파일 및 폴더 정보를 <file_map>과 <file_contents> 형식으로 클립보드에 복사
        """
        if not self.current_folder or self.checked_files == 0:
            self.statusBar().showMessage("선택된 파일이 없습니다.", 3000)
            return
        
        try:
            # 체크된 항목 정보 수집
            checked_items = []
            processed_count = 0
            
            # 디버깅 로깅 추가
            logger.debug(f"클립보드 복사 시작: {len(self.checked_items)}개 항목")
            
            for path_str in self.checked_items:
                try:
                    # 경로 객체로 변환
                    path = Path(path_str)
                    
                    # 절대 경로 확인
                    if not path.is_absolute():
                        abs_path = self.current_folder / path
                    else:
                        abs_path = path
                    
                    # 경로가 존재하는지 확인
                    if not abs_path.exists():
                        logger.warning(f"경로가 존재하지 않습니다: {abs_path}")
                        continue
                    
                    # 디렉토리 여부 확인 (파일 시스템에서 직접 확인)
                    is_dir = abs_path.is_dir()
                    
                    # 상대 경로 계산 (현재 폴더 기준)
                    try:
                        rel_path = abs_path.relative_to(self.current_folder)
                    except ValueError:
                        # 상대 경로를 계산할 수 없는 경우 파일 이름만 사용
                        rel_path = Path(abs_path.name)
                        logger.warning(f"상대 경로를 계산할 수 없습니다: {abs_path}, 파일 이름만 사용: {rel_path}")
                    
                    # 파일인 경우 바이너리 여부 추가 검사
                    if not is_dir:
                        # 해당 경로의 트리 아이템 찾기
                        item = self._find_item_by_path(abs_path)
                        
                        # 아이템이 없는 경우 건너뜀
                        if item is None:
                            logger.warning(f"트리 아이템을 찾을 수 없습니다: {abs_path}")
                            continue
                        
                        # 바이너리 파일은 제외
                        if item.data(Qt.UserRole + 1):
                            logger.info(f"바이너리 파일 제외: {abs_path}")
                            continue
                    
                    # 상세 디버깅 로깅
                    logger.debug(f"항목 추가: {rel_path}, is_dir={is_dir}")
                    
                    # 아이템 정보 추가
                    checked_items.append({
                        'path': abs_path,
                        'rel_path': rel_path,
                        'is_dir': is_dir
                    })
                    processed_count += 1
                    
                except Exception as e:
                    logger.warning(f"항목 정보 수집 중 오류 (건너뜀): {e}", exc_info=True)
                    continue
            
            if not checked_items:
                self.statusBar().showMessage("복사할 유효한 항목이 없습니다.", 3000)
                return
            
            logger.info(f"복사할 항목 수집 완료: {len(checked_items)}개 항목")
            
            # 항목 검증
            for item in checked_items:
                if not isinstance(item.get('rel_path'), Path):
                    logger.warning(f"rel_path가 Path 객체가 아닙니다: {item}")
                    item['rel_path'] = Path(str(item['rel_path']))
                    
                if 'is_dir' not in item:
                    logger.warning(f"is_dir이 없는 항목: {item}")
                    item['is_dir'] = item['path'].is_dir() if 'path' in item else False
            
            # <file_map>과 <file_contents> 생성
            try:
                result = generate_full_output(checked_items, self.current_folder)
            except Exception as e:
                logger.error(f"출력 생성 중 오류: {e}", exc_info=True)
                self.statusBar().showMessage("출력 형식 생성 실패", 5000)
                error_box = QMessageBox(self)
                error_box.setObjectName("critical")
                error_box.setWindowTitle("출력 형식 오류")
                error_box.setText(f"파일 구조를 형식화하는 중 오류가 발생했습니다.\n\n{str(e)}")
                error_box.setIcon(QMessageBox.Critical)
                error_box.exec()
                return
            
            # 클립보드에 복사
            if copy_to_clipboard(result):
                # 성공 메시지 표시 (선택 파일 수와 토큰 수 포함)
                self.statusBar().showMessage(
                    f"{self.checked_files}개 파일 ({self.total_tokens} 토큰) 클립보드에 복사됨", 
                    5000
                )
                logger.info(f"클립보드 복사 성공: {self.checked_files}개 파일, {self.total_tokens} 토큰")
            else:
                # 실패 메시지 표시
                self.statusBar().showMessage("클립보드 복사 실패", 5000)
                logger.error("클립보드 복사 실패")
                
        except Exception as e:
            logger.error(f"클립보드 복사 중 오류: {e}", exc_info=True)
            self.statusBar().showMessage(f"복사 중 오류 발생: {str(e)}", 5000)
            # 오류 메시지 박스 표시
            error_box = QMessageBox(self)
            error_box.setObjectName("critical")
            error_box.setWindowTitle("복사 오류")
            error_box.setText(f"클립보드에 복사하는 중 오류가 발생했습니다.\n\n{str(e)}")
            error_box.setIcon(QMessageBox.Critical)
            error_box.exec()
    
    def _show_settings_dialog(self):
        """설정 대화상자 표시"""
        try:
            dialog = SettingsDialog(
                self.tokenizer.get_available_models(),
                self.tokenizer.model_name,
                self
            )
            
            if dialog.exec() == QDialog.Accepted:
                try:
                    new_model = dialog.get_selected_model()
                    self.tokenizer.set_model(new_model)
                    self._update_token_count()
                    self.statusBar().showMessage(f"토큰화 모델 변경됨: {new_model}", 5000)
                except Exception as e:
                    logger.error(f"설정 적용 중 오류: {str(e)}")
                    error_box = QMessageBox(self)
                    error_box.setObjectName("critical")
                    error_box.setWindowTitle("오류")
                    error_box.setText(f"설정을 적용하는 중 오류가 발생했습니다:\n{str(e)}")
                    error_box.setIcon(QMessageBox.Critical)
                    error_box.exec()
        except Exception as e:
            logger.error(f"설정 대화상자 표시 중 오류: {str(e)}")
            error_box = QMessageBox(self)
            error_box.setObjectName("critical")
            error_box.setWindowTitle("오류")
            error_box.setText(f"설정 다이얼로그를 표시하는 중 오류가 발생했습니다:\n{str(e)}")
            error_box.setIcon(QMessageBox.Critical)
            error_box.exec()
    
    def _on_item_expanded(self, index):
        """트리 항목이 확장되었을 때 호출됨"""
        item = self.tree_model.itemFromIndex(index)
        if item and item.data(Qt.UserRole) is True:  # 디렉토리인 경우만
            item.setIcon(self.folder_open_icon)
    
    def _on_item_collapsed(self, index):
        """트리 항목이 축소되었을 때 호출됨"""
        item = self.tree_model.itemFromIndex(index)
        if item and item.data(Qt.UserRole) is True:  # 디렉토리인 경우만
            item.setIcon(self.folder_icon)

    def _center_window(self):
        """윈도우를 화면 중앙에 배치"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.geometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)

    def closeEvent(self, event):
        """프로그램 종료 시 처리"""
        # 토큰화 스레드 종료
        if self.token_thread and self.token_thread.isRunning():
            self.token_thread.stop()
            self.token_thread.wait()
        
        # 현재 설정 저장
        try:
            # 현재 설정 수집
            settings = {
                "model_name": self.tokenizer.model_name,
                "show_hidden_files": self.show_hidden_files_cb.isChecked(),
                "apply_gitignore": self.apply_gitignore_cb.isChecked(),
                "follow_symlinks": False
            }
            
            # 마지막으로 열었던 폴더 저장
            if self.current_folder:
                settings["last_directory"] = str(self.current_folder)
            
            # 설정 저장
            self.settings_manager.update_settings(settings)
            self.settings_manager.save_settings()
            logger.info("애플리케이션 종료 시 설정 저장됨")
        except Exception as e:
            logger.error(f"설정 저장 중 오류: {e}")
            
        event.accept()
        
    def _handle_copy_error(self, error_text: str):
        """복사 오류 처리"""
        logger.error(f"복사 오류: {error_text}")
        msg_box = QMessageBox(self)
        msg_box.setObjectName("critical")
        msg_box.setWindowTitle("오류")
        msg_box.setText(f"클립보드에 복사하는 중 오류가 발생했습니다:\n{error_text}")
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.exec() 