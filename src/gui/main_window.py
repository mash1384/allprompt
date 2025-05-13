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

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QFileDialog, QTreeView, QStatusBar,
    QMessageBox, QProgressBar, QMenu, QMenuBar, QApplication,
    QStyle, QCheckBox, QSizePolicy, QDialog, QDialogButtonBox, QFormLayout,
    QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, QSize, QDir, Signal, Slot, QThread, QSortFilterProxyModel, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction, QFont, QDesktopServices

# 파일 스캐너 모듈 임포트
from core.file_scanner import scan_directory, is_binary_file, read_text_file
# 토큰화 모듈 임포트
from core.tokenizer import Tokenizer
# .gitignore 필터링 모듈 임포트
from core.filter import GitignoreFilter
# 출력 포맷팅 모듈 임포트
from core.output_formatter import generate_file_map, generate_file_contents, generate_full_output
# 클립보드 유틸리티 모듈 임포트
from utils.clipboard_utils import copy_to_clipboard
from utils.settings_manager import SettingsManager
from gui.settings_dialog import SettingsDialog
from core.sort_utils import sort_items  # 정렬 유틸리티 임포트

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
        
        # 기본 UI 설정
        self.setWindowTitle("LLM 프롬프트 헬퍼")
        self.setMinimumSize(800, 600)
        
        # 중앙 위젯 및 레이아웃 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 상태 표시줄 설정
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 진행 표시줄 설정
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
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
        self.status_bar.showMessage("폴더를 선택하세요.", 5000)
        
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
        """기본 UI 구성"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # 메인 스플리터 (좌측: 트리 뷰, 우측: 제어 패널)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # ======= 좌측 패널 (트리 뷰) =======
        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")  # 스타일시트 적용을 위한 objectName 설정
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)
        
        # 파일/폴더 헤더 레이블 추가
        files_header = QLabel("파일/폴더")
        files_header.setObjectName("panelHeader")
        left_layout.addWidget(files_header)
        
        # 트리 뷰
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setHeaderHidden(False)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setEditTriggers(QTreeView.NoEditTriggers)
        self.tree_view.setSelectionMode(QTreeView.SingleSelection)
        self.tree_view.setHeaderHidden(False)
        
        # 트리 설정
        self.tree_view.setIndentation(20)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.header().setDefaultSectionSize(250)
        
        # 트리 모델 변경 시그널 연결
        self.tree_model.itemChanged.connect(self._on_item_changed)
        
        # 트리 확장/축소 시그널 연결
        self.tree_view.expanded.connect(self._on_item_expanded)
        self.tree_view.collapsed.connect(self._on_item_collapsed)
        
        left_layout.addWidget(self.tree_view)
        
        # 필터 옵션
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(15)
        
        # 숨김 파일/폴더 표시 체크박스
        self.show_hidden_cb = QCheckBox("숨김 파일/폴더 표시")
        show_hidden = self.settings_manager.get_setting("show_hidden_files", False)
        self.show_hidden_cb.setChecked(show_hidden)
        self.show_hidden_cb.toggled.connect(self._toggle_hidden_files)
        filter_layout.addWidget(self.show_hidden_cb)
        
        # .gitignore 규칙 적용 체크박스
        self.apply_gitignore_cb = QCheckBox(".gitignore 규칙 적용")
        apply_gitignore = self.settings_manager.get_setting("apply_gitignore", True)
        self.apply_gitignore_cb.setChecked(apply_gitignore)
        self.apply_gitignore_cb.toggled.connect(self._toggle_gitignore_filter)
        filter_layout.addWidget(self.apply_gitignore_cb)
        
        left_layout.addLayout(filter_layout)
        
        # ======= 우측 패널 (제어 영역) =======
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")  # 스타일시트 적용을 위한 objectName 설정
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(16)  # 섹션 간 간격 증가
        
        # ----- 폴더 선택 영역 -----
        folder_section_layout = QVBoxLayout()
        folder_section_layout.setSpacing(12)
        
        folder_header = QLabel("폴더 선택")
        folder_header.setObjectName("panelHeader")
        folder_section_layout.addWidget(folder_header)
        
        # 폴더 열기 버튼
        self.open_btn = QPushButton("폴더 열기")
        self.open_btn.setObjectName("openFolderButton")
        self.open_btn.clicked.connect(self._open_folder_dialog)
        folder_section_layout.addWidget(self.open_btn)
        
        # 현재 폴더 경로 표시
        path_layout = QVBoxLayout()
        path_layout.setSpacing(6)
        
        path_label = QLabel("폴더:")
        path_label.setObjectName("infoGroupLabel")
        path_layout.addWidget(path_label)
        
        self.folder_label = QLabel("없음")
        self.folder_label.setObjectName("pathLabel")
        self.folder_label.setWordWrap(True)
        path_layout.addWidget(self.folder_label)
        
        folder_section_layout.addLayout(path_layout)
        right_layout.addLayout(folder_section_layout)
        
        # ----- 선택 정보 영역 -----
        info_section_layout = QVBoxLayout()
        info_section_layout.setSpacing(12)
        
        info_header = QLabel("선택 정보")
        info_header.setObjectName("panelHeader")
        info_section_layout.addWidget(info_header)
        
        # 선택된 파일 수 정보
        files_info_layout = QHBoxLayout()
        files_info_layout.setSpacing(8)
        
        files_label = QLabel("파일:")
        files_label.setObjectName("infoGroupLabel")
        files_info_layout.addWidget(files_label)
        
        self.selected_files_label = QLabel("0")
        self.selected_files_label.setObjectName("infoValueLabel")
        files_info_layout.addWidget(self.selected_files_label)
        files_info_layout.addStretch(1)
        
        info_section_layout.addLayout(files_info_layout)
        
        # 토큰 수 정보
        token_info_layout = QHBoxLayout()
        token_info_layout.setSpacing(8)
        
        token_label = QLabel("토큰:")
        token_label.setObjectName("infoGroupLabel")
        token_info_layout.addWidget(token_label)
        
        self.token_label = QLabel("0")
        self.token_label.setObjectName("counterLabel")
        token_info_layout.addWidget(self.token_label)
        token_info_layout.addStretch(1)
        
        info_section_layout.addLayout(token_info_layout)
        right_layout.addLayout(info_section_layout)
        
        # ----- 작업 영역 -----
        action_section_layout = QVBoxLayout()
        action_section_layout.setSpacing(12)
        
        action_header = QLabel("작업")
        action_header.setObjectName("panelHeader")
        action_section_layout.addWidget(action_header)
        
        # 작업 버튼 영역
        self.copy_btn = QPushButton("클립보드에 복사")
        self.copy_btn.setObjectName("copyButton")
        self.copy_btn.setEnabled(False)  # 초기 비활성화
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        self.copy_btn.setMinimumHeight(40)  # 버튼 높이 증가
        action_section_layout.addWidget(self.copy_btn)
        
        right_layout.addLayout(action_section_layout)
        
        # 나머지 공간을 채우는 빈 영역
        right_layout.addStretch(1)
        
        # 스플리터에 패널 추가
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # 스플리터 비율 설정 (좌: 2, 우: 1)
        splitter.setSizes([2 * self.width() // 3, self.width() // 3])
        
        # 상태 표시줄
        self.status_bar = self.statusBar()
        
        # 프로그레스 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        logger.info("UI 구성 요소 초기화 완료")
    
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
            self.folder_label.setText(folder_path)
            self.selected_files_label.setText("0")
            self.token_label.setText("0")
            self.copy_btn.setEnabled(False)
            
            # .gitignore 필터 초기화
            apply_gitignore = self.apply_gitignore_cb.isChecked()
            if apply_gitignore:
                self.gitignore_filter = GitignoreFilter(folder_path)
                if self.gitignore_filter.has_gitignore():
                    self.status_bar.showMessage(f".gitignore 규칙을 적용합니다: {self.gitignore_filter.get_gitignore_path()}", 5000)
                else:
                    self.status_bar.showMessage(".gitignore 파일이 없습니다. 필터링 없이 모든 파일이 표시됩니다.", 5000)
                    self.gitignore_filter = None
            else:
                self.gitignore_filter = None
                
            # 파일 및 폴더 스캔
            include_hidden = self.show_hidden_cb.isChecked()
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
                    self.status_bar.showMessage(f"{ignored_count}개 항목이 .gitignore 규칙으로 필터링되었습니다.", 5000)
            
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
                self.status_bar.showMessage(f"{venv_count}개 가상환경 폴더가 필터링되었습니다.", 5000)
            
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
            self.status_bar.showMessage(f"오류: {str(e)}", 5000)
    
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
            
            # 기본 정보 수집 (툴큐용)
            file_info = []
            file_info.append(f"경로: {path}")
            
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
                self.selected_files_label.setText(f"{self.checked_files}")
                
                # 복사 버튼 활성화 상태 업데이트
                self.copy_btn.setEnabled(self.checked_files > 0)
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
        else:
            parent.setCheckState(Qt.Unchecked)
        
        # 부모 경로 가져오기
        parent_path = self._get_item_path(parent)
        if parent_path:
            is_dir = parent_path.is_dir()
            path_str = str(parent_path)
            
            # 부모가 체크되었는지 여부
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
        self.status_bar.showMessage(f"토큰 계산 중... (0/{len(files)} 파일)")
        
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
        self.status_bar.showMessage(f"토큰 계산 중... ({current}/{total} 파일)")
    
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
            self.token_label.setText(f"{self.total_tokens:,}")
    
    def _on_token_calculation_finished(self):
        """토큰 계산 완료 시 호출"""
        # 프로그레스 바 숨기기
        self.progress_bar.setVisible(False)
        
        # 상태 메시지 업데이트
        total_files = len(self.token_cache)
        self.status_bar.showMessage(f"토큰 계산 완료 ({total_files} 파일)", 5000)
        
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
        self.status_bar.showMessage(f"토큰 계산 중 오류: {error_msg}", 10000)
    
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
        self.token_label.setText(f"{self.total_tokens:,}")
        self.selected_files_label.setText(f"{self.checked_files}")
        
        # 제외된 파일이 있으면 상태 표시줄에 정보 표시
        if excluded_files > 0:
            self.status_bar.showMessage(f"{excluded_files}개 파일이 토큰 계산에서 제외됨 (바이너리 파일 또는 오류)", 5000)
        
        # 복사 버튼 활성화 상태 업데이트
        self.copy_btn.setEnabled(self.checked_files > 0)
    
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
        QMessageBox.about(
            self,
            "LLM 프롬프트 헬퍼 정보",
            "LLM 프롬프트 헬퍼 v0.1.0\n\n"
            "LLM 프롬프트용 코드 스니펫 생성 도우미\n"
            "© 2023"
        )
    
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
            self.status_bar.showMessage("선택된 파일이 없습니다.", 3000)
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
                self.status_bar.showMessage("복사할 유효한 항목이 없습니다.", 3000)
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
                self.status_bar.showMessage("출력 형식 생성 실패", 5000)
                QMessageBox.critical(
                    self,
                    "출력 형식 오류",
                    f"파일 구조를 형식화하는 중 오류가 발생했습니다.\n\n{str(e)}"
                )
                return
            
            # 클립보드에 복사
            if copy_to_clipboard(result):
                # 성공 메시지 표시 (선택 파일 수와 토큰 수 포함)
                self.status_bar.showMessage(
                    f"{self.checked_files}개 파일 ({self.total_tokens} 토큰) 클립보드에 복사됨", 
                    5000
                )
                logger.info(f"클립보드 복사 성공: {self.checked_files}개 파일, {self.total_tokens} 토큰")
            else:
                # 실패 메시지 표시
                self.status_bar.showMessage("클립보드 복사 실패", 5000)
                logger.error("클립보드 복사 실패")
                
        except Exception as e:
            logger.error(f"클립보드 복사 중 오류: {e}", exc_info=True)
            self.status_bar.showMessage(f"복사 중 오류 발생: {str(e)}", 5000)
            # 오류 메시지 박스 표시
            QMessageBox.critical(
                self,
                "복사 오류",
                f"클립보드에 복사하는 중 오류가 발생했습니다.\n\n{str(e)}"
            )
    
    def _show_settings_dialog(self):
        """설정 다이얼로그 표시"""
        try:
            # 현재 설정 가져오기
            current_settings = {
                "model_name": self.tokenizer.model_name,
                "show_hidden_files": self.show_hidden_cb.isChecked(),
                "apply_gitignore": self.apply_gitignore_cb.isChecked(),
                "follow_symlinks": False
            }
            
            # 설정 다이얼로그 생성 및 표시
            dialog = SettingsDialog(self, current_settings)
            
            # 설정 변경 시그널 연결
            dialog.settings_changed.connect(self._on_settings_changed)
            
            # 다이얼로그 실행
            if dialog.exec():
                # 사용자가 OK를 클릭한 경우, 설정 가져오기
                new_settings = dialog.get_settings()
                
                # 설정 적용
                self._on_settings_changed(new_settings)
        except Exception as e:
            logger.error(f"설정 다이얼로그 표시 중 오류: {e}")
            QMessageBox.critical(self, "오류", f"설정 다이얼로그를 표시하는 중 오류가 발생했습니다:\n{str(e)}")
    
    def _on_settings_changed(self, settings):
        """
        설정 변경 처리
        
        Args:
            settings: 새 설정 딕셔너리
        """
        try:
            logger.info(f"설정 변경: {settings}")
            
            # 모델 변경 시 토크나이저 다시 생성
            if settings.get("model_name") != self.tokenizer.model_name:
                old_model = self.tokenizer.model_name
                new_model = settings.get("model_name")
                
                self.tokenizer = Tokenizer(new_model)
                logger.info(f"토큰화 모델 변경: {old_model} -> {new_model}")
                
                # 토큰 계산 캐시 초기화
                self.token_cache.clear()
                
                # 토큰 수 재계산 (현재 선택된 파일들)
                self._update_token_count()
                
                # 상태 메시지 표시
                self.status_bar.showMessage(f"토큰화 모델 변경됨: {new_model}", 5000)
            
            # 숨김 파일 표시 설정 변경 시
            if settings.get("show_hidden_files") != self.show_hidden_cb.isChecked():
                self.show_hidden_cb.setChecked(settings.get("show_hidden_files"))
                
                # 현재 폴더가 있는 경우 다시 로드
                if self.current_folder:
                    self._load_folder(str(self.current_folder))
            
            # 설정 파일에 저장
            self.settings_manager.update_settings(settings)
            self.settings_manager.save_settings()
            
        except Exception as e:
            logger.error(f"설정 적용 중 오류: {e}")
            QMessageBox.critical(self, "오류", f"설정을 적용하는 중 오류가 발생했습니다:\n{str(e)}")
    
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
                "show_hidden_files": self.show_hidden_cb.isChecked(),
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