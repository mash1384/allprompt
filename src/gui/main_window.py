#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
메인 윈도우 모듈
애플리케이션의 주요 UI 구성 요소를 정의합니다.
"""

import logging
import os
from pathlib import Path
import appdirs
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
    QLineEdit, QComboBox, QStyledItemDelegate, QProxyStyle, QStyleOptionViewItem
)
from PySide6.QtCore import Qt, QSize, QDir, Signal, Slot, QThread, QSortFilterProxyModel, QModelIndex, QEvent, QObject, QRect
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction, QFont, QDesktopServices, QPainter, QCursor

# 커스텀 위젯 임포트
from .custom_widgets import CustomTreeView, CheckableItemDelegate
from .panels import LeftPanelWidget, RightPanelWidget
# 컨트롤러 임포트
from .controllers import FileTreeController
from .token_controller import TokenController
from .action_controller import ActionController
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

class MainWindow(QMainWindow):
    """메인 애플리케이션 윈도우"""
    
    def __init__(self):
        """Initialize the main window"""
        super().__init__()
        
        self.setWindowTitle("allprompt")
        
        # Initialize progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # 파일 캐시 초기화 
        self.file_cache = {}   # Cache for file contents {file_path: content}
        
        # 아이콘 초기화
        self._init_icons()
        
        # Initialize FileTreeController
        self.file_tree_controller = FileTreeController(
            folder_icon=self.folder_icon,
            folder_open_icon=self.folder_open_icon,
            file_icon=self.file_icon,
            code_file_icon=self.code_file_icon,
            doc_file_icon=self.doc_file_icon,
            symlink_icon=self.symlink_icon,
            binary_icon=self.binary_icon,
            error_icon=self.error_icon,
            image_file_icon=self.image_file_icon
        )
        
        # Initialize TokenController
        self.token_controller = TokenController(self)
        
        # Initialize ActionController
        self.action_controller = ActionController()
        
        # UI 초기화 전 컨트롤러 시그널 연결
        self._connect_controller_signals()
        
        # Initialize UI components
        self._init_ui()
        
        # Center the window on screen
        self._center_window()
        
        logger.info("Main window initialized")
        
    def _connect_controller_signals(self):
        """컨트롤러 시그널 연결"""
        # FileTreeController 시그널 연결
        self.file_tree_controller.folder_loaded_signal.connect(self._on_folder_loaded)
        self.file_tree_controller.selection_changed_signal.connect(self._on_selection_changed)
        self.file_tree_controller.model_updated_signal.connect(self._on_model_updated)
        
        # TokenController 시그널 연결
        self.token_controller.token_progress_signal.connect(self._update_progress_bar)
        self.token_controller.total_tokens_updated_signal.connect(self._update_token_label)
        self.token_controller.token_calculation_status_signal.connect(self._update_status_message)
        
        # ActionController 시그널 연결
        self.action_controller.copy_status_signal.connect(self._handle_copy_status)
    
    def _update_progress_bar(self, current: int, total: int):
        """
        프로그레스 바 업데이트
        
        Args:
            current: 현재 값
            total: 전체 값
        """
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
        else:
            self.progress_bar.setValue(0)
    
    def _update_token_label(self, token_count_str: str):
        """
        토큰 수 레이블 업데이트
        
        Args:
            token_count_str: 포맷팅된 토큰 수 문자열
        """
        files_count = self.file_tree_controller.get_checked_files_count()
        self.right_panel.update_selection_info(f"{files_count}", token_count_str)
    
    def _update_status_message(self, message: str, is_error: bool):
        """
        상태 표시줄 메시지 업데이트
        
        Args:
            message: 표시할 메시지
            is_error: 오류 메시지 여부
        """
        if is_error:
            self.statusBar().showMessage(message, 5000)  # 5초간 표시
        else:
            self.statusBar().showMessage(message, 3000)  # 3초간 표시
        
    def _init_icons(self):
        """아이콘 리소스 초기화"""
        # 커스텀 SVG 아이콘 사용
        self.folder_icon = QIcon(":/icons/folder.svg")
        self.folder_open_icon = QIcon(":/icons/folder_open.svg")
        self.file_icon = QIcon(":/icons/file_document.svg")
        self.code_file_icon = QIcon(":/icons/file_code.svg")
        self.doc_file_icon = QIcon(":/icons/file_document.svg")
        self.copy_icon = QIcon(":/icons/copy_document.svg")
        self.clear_icon = QIcon(":/icons/clear_selection.svg")
        
        # 일부 특별한 아이콘은 시스템 아이콘 유지
        style = self.style()
        self.symlink_icon = style.standardIcon(QStyle.SP_FileLinkIcon)
        self.binary_icon = style.standardIcon(QStyle.SP_DriveHDIcon)
        self.error_icon = style.standardIcon(QStyle.SP_MessageBoxCritical)
        self.image_file_icon = style.standardIcon(QStyle.SP_DirLinkIcon)
        
        # 자주 사용되는 파일 확장자별 아이콘 매핑
        self.extension_icon_map = {
            # 코드 파일 확장자
            '.py': self.code_file_icon,
            '.js': self.code_file_icon,
            '.html': self.code_file_icon,
            '.css': self.code_file_icon,
            '.cpp': self.code_file_icon,
            '.h': self.code_file_icon,
            '.java': self.code_file_icon,
            '.ts': self.code_file_icon,
            '.tsx': self.code_file_icon,
            '.jsx': self.code_file_icon,
            '.go': self.code_file_icon,
            '.rs': self.code_file_icon,
            '.php': self.code_file_icon,
            
            # 문서 파일 확장자
            '.md': self.doc_file_icon,
            '.txt': self.doc_file_icon,
            '.pdf': self.doc_file_icon,
            '.docx': self.doc_file_icon,
            '.xlsx': self.doc_file_icon,
            '.pptx': self.doc_file_icon,
            '.json': self.doc_file_icon,
            '.yaml': self.doc_file_icon,
            '.yml': self.doc_file_icon,
            '.xml': self.doc_file_icon,
            '.csv': self.doc_file_icon,
            
            # 이미지 파일 확장자
            '.jpg': self.image_file_icon,
            '.jpeg': self.image_file_icon,
            '.png': self.image_file_icon,
            '.gif': self.image_file_icon,
            '.svg': self.image_file_icon,
            '.webp': self.image_file_icon,
            '.bmp': self.image_file_icon,
            '.ico': self.image_file_icon,
        }

    def _init_ui(self):
        """UI 구성요소 초기화"""
        logger.info("메인 UI 초기화 시작")
        # 중앙 위젯 생성
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 스플리터 생성 - 좌측/우측 패널 구분
        splitter = QSplitter(Qt.Horizontal)
        
        # 좌측 패널 (파일 트리 영역)
        self.left_panel = LeftPanelWidget(
            folder_icon=self.folder_icon,
            folder_open_icon=self.folder_open_icon,
            file_icon=self.file_icon,
            code_file_icon=self.code_file_icon,
            doc_file_icon=self.doc_file_icon,
            symlink_icon=self.symlink_icon,
            binary_icon=self.binary_icon,
            error_icon=self.error_icon,
            image_file_icon=self.image_file_icon
        )
        # 우측 패널 (정보 및 액션 영역)
        self.right_panel = RightPanelWidget(
            folder_icon=self.folder_icon,
            copy_icon=self.copy_icon,
            clear_icon=self.clear_icon
        )
        
        # 초기 너비 설정
        self.left_panel.setMinimumWidth(360)
        self.right_panel.setMinimumWidth(260)
        self.right_panel.setMaximumWidth(400)
        
        # 패널을 스플리터에 추가
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)
        
        # 스플리터 비율 설정 (4:1)
        splitter.setSizes([400, 100])
        
        # 메인 레이아웃에 스플리터 추가
        main_layout.addWidget(splitter)
        
        # 프로그레스 바 추가
        self.progress_bar.setTextVisible(True)  # 퍼센트 표시
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        main_layout.addWidget(self.progress_bar)
        
        # 중앙 위젯 설정
        self.setCentralWidget(main_widget)
        
        # 상태 표시줄 생성
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 메뉴바 생성
        self._create_menu()
        
        # 이벤트 연결
        self._connect_events()
        
        # 크기 설정
        self.resize(900, 650)
        
        logger.info("메인 UI 초기화 완료")
        
    def _connect_events(self):
        """UI 이벤트 연결"""
        # 좌측 패널 이벤트 연결
        tree_view = self.left_panel.get_tree_view()
        # 불필요한 doubleClicked 이벤트 연결 제거 (CustomTreeView에서 이미 처리)
        tree_view.expanded.connect(self._on_item_expanded)
        tree_view.collapsed.connect(self._on_item_collapsed)
        
        # 우측 패널 이벤트 연결
        self.right_panel.open_folder_button.clicked.connect(self._open_folder_dialog)
        self.right_panel.copy_button.clicked.connect(self._copy_to_clipboard)
        self.right_panel.clear_button.clicked.connect(self._clear_selection)
        
        # 컨트롤러가 제공하는 모델로 트리 모델 설정
        tree_model = self.file_tree_controller.get_tree_model()
        self.left_panel.set_tree_model(tree_model)
    
    def _create_menu(self):
        """메뉴바 생성"""
        menubar = QMenuBar()
        
        # 파일 메뉴
        file_menu = QMenu("&File", self)
        
        # 열기 액션
        open_action = QAction(self.folder_icon, "&Open Folder", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_folder_dialog)
        
        # 클립보드 복사 액션
        copy_action = QAction(self.copy_icon, "&Copy to Clipboard", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self._copy_to_clipboard)
        
        # 종료 액션
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        
        # 파일 메뉴에 액션 추가
        file_menu.addAction(open_action)
        file_menu.addAction(copy_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # 보기 메뉴
        view_menu = QMenu("&View", self)
        
        # 숨김 파일 표시 액션
        self.show_hidden_action = QAction("Show &Hidden Files", self)
        self.show_hidden_action.setCheckable(True)
        self.show_hidden_action.setChecked(False)
        self.show_hidden_action.triggered.connect(self._toggle_hidden_files)
        
        # .gitignore 필터링 액션
        self.gitignore_filter_action = QAction("Apply .&gitignore Rules", self)
        self.gitignore_filter_action.setCheckable(True)
        self.gitignore_filter_action.setChecked(True)  # 기본값을 컨트롤러 설정과 일치시킴
        self.gitignore_filter_action.triggered.connect(self._toggle_gitignore_filter)
        
        # 보기 메뉴에 액션 추가
        view_menu.addAction(self.show_hidden_action)
        view_menu.addAction(self.gitignore_filter_action)
        
        # 도움말 메뉴
        help_menu = QMenu("&Help", self)
        
        # 정보 액션
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about_dialog)
        
        # 도움말 메뉴에 액션 추가
        help_menu.addAction(about_action)
        
        # 메뉴를 메뉴바에 추가
        menubar.addMenu(file_menu)
        menubar.addMenu(view_menu)
        menubar.addMenu(help_menu)
        
        # 메뉴바 설정
        self.setMenuBar(menubar)
        
    def _open_folder_dialog(self):
        """폴더 열기 대화상자 표시"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            QDir.homePath()
        )
        
        if folder_path:
            self._load_folder(folder_path)
    
    def _load_folder(self, folder_path: str):
        """
        폴더 로드 및 표시
        
        Args:
            folder_path: 로드할 폴더 경로
        """
        try:
            # UI 상태 초기화
            self.progress_bar.setValue(0)
            self.statusBar().showMessage("Loading folder...")
            
            # 컨트롤러에 폴더 로드 위임
            # 폴더 로드 완료 후 folder_loaded_signal을 통해 _on_folder_loaded 호출됨
            self.file_tree_controller.load_folder(folder_path)
            
        except Exception as e:
            # 오류 처리
            self.statusBar().showMessage(f"Error loading folder: {str(e)}", 5000)
            QMessageBox.critical(
                self,
                "Folder Loading Error",
                f"An error occurred while loading the folder:\n{str(e)}"
            )
            logger.error(f"Folder loading error: {str(e)}", exc_info=True)
    
    def _show_about_dialog(self):
        """About 대화상자 표시"""
        dialog = QDialog(self)
        dialog.setWindowTitle("About allprompt")
        
        layout = QVBoxLayout(dialog)
        
        # 앱 이름 및 버전
        app_label = QLabel("<h2>allprompt</h2>")
        app_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(app_label)
        
        # 설명
        desc_label = QLabel(
            "<p>A utility for generating prompt-friendly code summaries.</p>"
            "<p>Use with AI assistants to help them understand your codebase structure.</p>"
        )
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 버전 정보
        version_label = QLabel("<p><b>Version:</b> 0.1.0</p>")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # 버튼 박스
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.setFixedWidth(400)
        dialog.exec()
        
    def _copy_to_clipboard(self):
        """선택된 파일 내용을 클립보드에 복사"""
        try:
            # 선택된 항목이 없는 경우
            if not self.file_tree_controller.get_checked_files_count():
                self.statusBar().showMessage("No files selected to copy", 3000)
                return
            
            # 상태 표시줄 업데이트
            self.statusBar().showMessage("Copying selected files to clipboard...")
            
            # 필요한 정보 수집 - FileTreeController에서 직접 가져오기
            root_path = self.file_tree_controller.get_current_folder()
            selected_item_paths = self.file_tree_controller.get_checked_items()
            total_tokens = self.token_controller.total_tokens
            
            # ActionController에 작업 위임
            self.action_controller.perform_copy_to_clipboard(
                root_path, 
                selected_item_paths, 
                total_tokens
            )
            
        except Exception as e:
            # 오류 처리
            self._handle_copy_error(str(e))
    
    def _handle_copy_error(self, error_text: str):
        """
        클립보드 복사 오류 처리
        
        Args:
            error_text: 오류 메시지
        """
        self.statusBar().showMessage(f"Clipboard copy error: {error_text}", 5000)
        QMessageBox.critical(
            self,
            "Clipboard Error",
            f"Failed to copy to clipboard:\n{error_text}"
        )
    
    def _toggle_hidden_files(self):
        """숨김 파일 표시 설정 토글"""
        # FileTreeController에 위임
        show_hidden = self.file_tree_controller.toggle_hidden_files()
        
        # 체크박스 상태 동기화
        self.show_hidden_action.setChecked(show_hidden)
    
    def _toggle_gitignore_filter(self):
        """gitignore 필터링 설정 토글"""
        # FileTreeController에 위임
        checked = self.file_tree_controller.toggle_gitignore_filter()
        
        # 체크박스 상태 동기화
        self.gitignore_filter_action.setChecked(checked)
    
    def _center_window(self):
        """윈도우를 화면 중앙에 위치시킴"""
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())
        
    def show(self):
        """윈도우 표시"""
        super().show()
        logger.info("Main window shown")
        
        # 초기 버튼 상태 설정
        self.right_panel.set_buttons_enabled(
            copy_enabled=False, 
            clear_enabled=False
        )
        
        # 시작 시 기본 폴더로 현작 디렉토리를 선택
        try:
            initial_dir = os.getcwd()
            self._load_folder(initial_dir)
        except Exception as e:
            logger.warning(f"Failed to load default folder: {e}")
    
    def closeEvent(self, event):
        """
        윈도우 닫기 이벤트 처리
        
        Args:
            event: 닫기 이벤트 객체
        """
        logger.info("Main window closing")
        
        # 진행 중인 토큰 계산 작업이 있으면 중지
        if hasattr(self, 'token_thread') and self.token_thread and self.token_thread.isRunning():
            self.token_thread.stop()
            self.token_thread.wait()
        
        event.accept()
    
    def _on_folder_loaded(self, items):
        """
        폴더 로드 완료 이벤트 처리
        
        Args:
            items: 로드된 항목 목록
        """
        # 초기 모두 확장 (루트만)
        tree_view = self.left_panel.get_tree_view()
        for row in range(tree_view.model().rowCount()):
            root_index = tree_view.model().index(row, 0)
            tree_view.expand(root_index)
        
        # 폴더 경로 업데이트
        current_folder = self.file_tree_controller.get_current_folder()
        if current_folder:
            self.right_panel.update_folder_path(str(current_folder))
        
        # 버튼 상태 업데이트
        self.right_panel.set_buttons_enabled(
            copy_enabled=False,
            clear_enabled=False
        )
        
        # 진행 표시줄 업데이트
        self.progress_bar.setValue(100)
        
        # 폴더 로드 완료 메시지
        if current_folder:
            self.statusBar().showMessage(f"Folder loaded: {current_folder}", 3000)
    
    def _on_selection_changed(self, files_count, dirs_count):
        """
        선택 변경 이벤트 처리
        
        Args:
            files_count: 선택된 파일 수
            dirs_count: 선택된 디렉토리 수
        """
        # 선택 정보 업데이트
        self.right_panel.update_selection_info(
            f"{files_count}",
            "계산 중..."
        )
        
        # 버튼 상태 업데이트
        has_selection = files_count > 0 or dirs_count > 0
        self.right_panel.set_buttons_enabled(
            copy_enabled=files_count > 0,
            clear_enabled=has_selection
        )
        
        # 토큰 계산 시작 (TokenController에 위임)
        # 컨트롤러에서 체크된 파일 항목만 필터링
        checked_items = self.file_tree_controller.get_checked_items()
        files_to_calculate = [Path(path) for path in checked_items if Path(path).is_file()]
        
        if files_to_calculate:
            self.token_controller.start_calculation(files_to_calculate)
    
    def _on_model_updated(self, model):
        """
        모델 업데이트 이벤트 처리
        
        Args:
            model: 업데이트된 모델
        """
        # 트리 모델을 좌측 패널에 설정
        self.left_panel.set_tree_model(model)
        
        # 트리 뷰 모델 변경 후에는 트리 뷰 스크롤 위치 초기화
        tree_view = self.left_panel.get_tree_view()
        tree_view.scrollToTop()
    
    def _handle_copy_status(self, success: bool, message: str):
        """
        클립보드 복사 상태 처리
        
        Args:
            success: 성공 여부
            message: 상태 메시지
        """
        if success:
            self.statusBar().showMessage(message, 3000)
        else:
            self.statusBar().showMessage(f"Error: {message}", 5000)
            QMessageBox.warning(
                self,
                "Copy Error",
                message
            )
    
    def _on_item_expanded(self, index):
        """
        항목 확장 이벤트 처리
        
        Args:
            index: 확장된 항목의 인덱스
        """
        self.left_panel.update_item_icon(index, 'folder_open')
    
    def _on_item_collapsed(self, index):
        """
        항목 축소 이벤트 처리
        
        Args:
            index: 축소된 항목의 인덱스
        """
        self.left_panel.update_item_icon(index, 'folder')
    
    def _clear_selection(self):
        """선택 항목 모두 해제"""
        # FileTreeController에 위임
        self.file_tree_controller.clear_selection()
        
        # 선택 정보 업데이트
        self.right_panel.update_selection_info("0", "0")
        
        # 버튼 상태 업데이트
        self.right_panel.set_buttons_enabled(
            copy_enabled=False,
            clear_enabled=False
        )
    