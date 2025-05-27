#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
메인 윈도우 모듈
애플리케이션의 주요 UI 구성 요소를 정의합니다.
"""

import logging
import os
import platform
import re
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QFileDialog, QTreeView, QStatusBar,
    QMessageBox, QProgressBar, QMenu, QMenuBar, QApplication,
    QStyle, QCheckBox, QSizePolicy, QDialog, QDialogButtonBox, QFormLayout,
    QLineEdit, QComboBox, QStyledItemDelegate, QProxyStyle, QStyleOptionViewItem
)
from PySide6.QtCore import Qt, QSize, QDir, Signal, Slot, QThread, QSortFilterProxyModel, QModelIndex, QEvent, QObject, QRect, QTimer
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
# 설정 관리자 임포트
from src.utils.settings_manager import SettingsManager
# 설정 다이얼로그 임포트
from .settings_dialog import SettingsDialog
# 상수 임포트
from src.core.constants import EXTENSION_TO_LANGUAGE_MAP

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """메인 애플리케이션 윈도우"""
    
    def __init__(self):
        """Initialize the main window"""
        super().__init__()
        
        self.setWindowTitle("allprompt")
        self.resize(1200, 800)
        
        # Initialize progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # 파일 캐시 초기화 
        self.file_cache = {}   # Cache for file contents {file_path: content}
        
        # 설정 관리자 초기화
        self.settings_manager = SettingsManager()
        
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
        
        # 설정값을 컨트롤러에 적용
        settings = self.settings_manager.get_all_settings()
        self.file_tree_controller.show_hidden = settings.get("show_hidden_files", False)
        self.file_tree_controller.apply_gitignore_rules = settings.get("apply_gitignore_rules", True)
        
        # Initialize TokenController
        self.token_controller = TokenController(self)
        
        # 토크나이저 모델 설정 (TokenController에 set_model 메서드가 없으므로 제거)
        # model_name = settings.get("model_name", "gpt-3.5-turbo")
        # self.token_controller.set_model(model_name)
        
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
        self.token_controller.total_tokens_updated_signal.connect(
            lambda token_count_str, files_count: self._update_token_label(token_count_str, files_count)
        )
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
    
    def _update_token_label(self, token_count_str: str, files_count=None):
        """
        토큰 수 레이블 업데이트
        
        Args:
            token_count_str: 포맷팅된 토큰 수 문자열
            files_count: 선택된 파일 수 (None인 경우 FileTreeController에서 가져옴)
        """
        if files_count is None:
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
        # 메인 위젯 및 레이아웃
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 메인 수직 레이아웃
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 스플리터 위젯 (좌/우 패널 분할)
        self.splitter = QSplitter(Qt.Horizontal)
        
        # 좌측 패널 (파일 트리)
        self.left_panel = LeftPanelWidget(
            parent=self.splitter,
            folder_icon=self.folder_icon,
            folder_open_icon=self.folder_open_icon
        )
        
        # 우측 패널 (정보 및 액션)
        self.right_panel = RightPanelWidget(
            parent=self.splitter,
            folder_icon=self.folder_icon,
            copy_icon=self.copy_icon,
            clear_icon=self.clear_icon
        )
        
        # 패널 초기 크기 설정
        self.splitter.setSizes([self.width() * 0.7, self.width() * 0.3])
        self.splitter.setStretchFactor(0, 7)  # 좌측 패널 (70%)
        self.splitter.setStretchFactor(1, 3)  # 우측 패널 (30%)
        
        # 메인 레이아웃에 스플리터 추가
        main_layout.addWidget(self.splitter)
        
        # 상태바 설정
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.progress_bar.setFixedWidth(150)
        self.statusBar().showMessage("Ready")
        
        # 메뉴 생성
        self._create_menu()
        
        # 이벤트 연결
        self._connect_events()
        
        # 컨트롤러가 제공하는 모델로 트리 모델 설정
        tree_model = self.file_tree_controller.get_tree_model()
        self.left_panel.set_tree_model(tree_model)
        
    def _connect_events(self):
        """UI 이벤트 연결"""
        # 폴더 열기 버튼 클릭
        self.right_panel.open_folder_button.clicked.connect(self._open_folder_dialog)
        
        # 복사 버튼 클릭
        self.right_panel.copy_button.clicked.connect(self._copy_to_clipboard)
        
        # 클리어 버튼 클릭
        self.right_panel.clear_button.clicked.connect(self._clear_selection)
        
        # 설정 버튼 클릭
        self.right_panel.settings_button.clicked.connect(self._open_settings_dialog)
        
        # 메뉴 옵션 이벤트 연결은 _create_menu에서 수행
        
        # 참고: 트리 뷰 확장/축소 및 클릭 이벤트는 LeftPanelWidget에서 자체적으로 처리됨
        # - 트리 확장/축소: self.tree_view.expanded/collapsed.connect(self.update_item_icon_on_expand/collapse)
        # - 파일 클릭: CustomTreeView.mouseReleaseEvent에서 처리
    
    def _create_menu(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("&File")
        
        # 폴더 열기 액션
        open_folder_action = QAction(self.folder_icon, "&Open Folder...", self)
        open_folder_action.setShortcut("Ctrl+O")
        open_folder_action.triggered.connect(self._open_folder_dialog)
        file_menu.addAction(open_folder_action)
        
        # 설정 액션
        settings_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "&Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._open_settings_dialog)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # 종료 액션
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 뷰 메뉴
        view_menu = menubar.addMenu("&View")
        
        # 현재 설정 가져오기
        current_settings = self.settings_manager.get_all_settings()
        
        # 숨김 파일 표시 토글
        self.show_hidden_action = QAction("Show &Hidden Files", self)
        self.show_hidden_action.setCheckable(True)
        self.show_hidden_action.setChecked(current_settings.get("show_hidden_files", False))
        self.show_hidden_action.triggered.connect(self._toggle_hidden_files)
        view_menu.addAction(self.show_hidden_action)
        
        # .gitignore 필터 토글
        self.gitignore_filter_action = QAction("Apply &.gitignore Rules", self)
        self.gitignore_filter_action.setCheckable(True)
        self.gitignore_filter_action.setChecked(current_settings.get("apply_gitignore_rules", True))
        self.gitignore_filter_action.triggered.connect(self._toggle_gitignore_filter)
        view_menu.addAction(self.gitignore_filter_action)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("&Help")
        
        # 정보 액션
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)
    
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
        지정된 폴더를 로드 및 UI 업데이트
        
        Args:
            folder_path: 로드할 폴더 경로
        """
        logger.info(f"폴더 로드 요청: {folder_path}")
        try:
            # FileTreeController를 통해 폴더 로드
            self.file_tree_controller.load_folder(folder_path)
            
            # 현재 폴더 경로 UI 업데이트
            current_folder = self.file_tree_controller.get_current_folder()
            if current_folder:
                self.right_panel.update_folder_path(str(current_folder))
                
                # 마지막 사용 디렉토리 저장
                self.settings_manager.set_setting('last_directory', str(current_folder))
                self.settings_manager.save_settings()
                logger.info(f"마지막 사용 디렉토리 저장: {current_folder}")
            
            logger.info(f"폴더 로드 성공: {folder_path}")
        except FileNotFoundError:
            logger.error(f"폴더를 찾을 수 없음: {folder_path}", exc_info=True)
            QMessageBox.critical(self, "Error Loading Folder", 
                               f"Folder not found: {folder_path}")
        except PermissionError:
            logger.error(f"폴더 접근 권한 없음: {folder_path}", exc_info=True)
            QMessageBox.critical(self, "Error Loading Folder", 
                               f"Permission denied for folder: {folder_path}")
        except Exception as e:
            logger.error(f"폴더 로드 중 오류: {e}", exc_info=True)
            QMessageBox.critical(self, "Error Loading Folder", 
                                f"Failed to load folder: {str(e)}")
    
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
            
            # 설정에서 파일트리만 복사 옵션 가져오기
            copy_file_tree_only = self.settings_manager.get_setting("copy_file_tree_only", False)
            
            # ActionController에 작업 위임
            self.action_controller.perform_copy_to_clipboard(
                root_path, 
                selected_item_paths, 
                total_tokens,
                copy_file_tree_only
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
        """숨김 파일 표시 여부 토글"""
        logger.info("숨김 파일 표시 토글")
        
        # 파일 트리 컨트롤러를 통해 토글
        show_hidden = self.file_tree_controller.toggle_hidden_files()
        
        # 설정 업데이트 및 저장
        self.settings_manager.set_setting("show_hidden_files", show_hidden)
        self.settings_manager.save_settings()
        
        # 현재 폴더 다시 로드 - FileTreeController에서 내부적으로 현재 폴더를 추적함
        if self.file_tree_controller.get_current_folder():
            self._load_folder(str(self.file_tree_controller.get_current_folder()))
    
    def _toggle_gitignore_filter(self):
        """gitignore 필터링 토글"""
        logger.info(".gitignore 필터 토글")
        
        # 파일 트리 컨트롤러를 통해 토글
        apply_gitignore = self.file_tree_controller.toggle_gitignore_filter()
        
        # 설정 업데이트 및 저장
        self.settings_manager.set_setting("apply_gitignore_rules", apply_gitignore)
        self.settings_manager.save_settings()
        
        # 현재 폴더 다시 로드 - FileTreeController에서 내부적으로 현재 폴더를 추적함
        if self.file_tree_controller.get_current_folder():
            self._load_folder(str(self.file_tree_controller.get_current_folder()))
    
    def _open_settings_dialog(self):
        """설정 다이얼로그 표시"""
        logger.info("설정 다이얼로그 열기")
        
        # 현재 설정 가져오기
        current_settings = self.settings_manager.get_all_settings()
        
        # 설정 다이얼로그 생성
        dialog = SettingsDialog(
            parent=self,
            current_settings=current_settings
        )
        
        # 설정 변경 시그널 연결
        dialog.settings_changed.connect(self._apply_settings)
        
        # 다이얼로그 표시
        dialog.exec()

    def _apply_settings(self, new_settings):
        """
        설정 변경 적용
        
        Args:
            new_settings: 새로운 설정 딕셔너리
        """
        logger.info(f"설정 변경 적용: {new_settings}")
        
        # 이전 설정 가져오기
        old_settings = self.settings_manager.get_all_settings()
        
        # 설정 업데이트
        self.settings_manager.update_settings(new_settings)
        self.settings_manager.save_settings()
        
        # 숨김 파일 표시 설정 변경 처리
        if old_settings.get("show_hidden_files") != new_settings.get("show_hidden_files"):
            logger.info(f"숨김 파일 표시 설정 변경: {new_settings.get('show_hidden_files')}")
            self.file_tree_controller.show_hidden = new_settings.get("show_hidden_files")
            self.show_hidden_action.setChecked(new_settings.get("show_hidden_files"))
        
        # gitignore 필터링 설정 변경 처리
        if old_settings.get("apply_gitignore_rules") != new_settings.get("apply_gitignore_rules"):
            logger.info(f".gitignore 필터링 설정 변경: {new_settings.get('apply_gitignore_rules')}")
            self.file_tree_controller.apply_gitignore_rules = new_settings.get("apply_gitignore_rules")
            self.gitignore_filter_action.setChecked(new_settings.get("apply_gitignore_rules"))
        
        # 파일트리만 복사 설정 변경 처리
        if old_settings.get("copy_file_tree_only") != new_settings.get("copy_file_tree_only"):
            logger.info(f"파일트리만 복사 설정 변경: {new_settings.get('copy_file_tree_only')}")
            # 이 설정은 복사할 때 적용되므로 여기서는 저장만 하고 실제 적용은 복사 시 처리
        
        # 현재 폴더가 로드되어 있으면 다시 스캔하여 설정 적용
        if (old_settings.get("show_hidden_files") != new_settings.get("show_hidden_files") or
            old_settings.get("apply_gitignore_rules") != new_settings.get("apply_gitignore_rules")) and \
            self.file_tree_controller.get_current_folder():
            self._load_folder(str(self.file_tree_controller.get_current_folder()))
        
        # 상태 메시지 표시
        self.statusBar().showMessage("설정이 저장되었습니다.", 3000)
    
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
        
        # 마지막 사용 디렉토리 로드 기능 비활성화
        # 사용자가 직접 폴더를 선택해야만 파일트리에 폴더가 표시됨
        logger.info("앱 시작 시 폴더 자동 로드 비활성화됨")
        
        # 초기 상태 설정 - 파일/폴더 없음
        self.right_panel.update_folder_path("")
        self.right_panel.update_selection_info("0", "0")
        self.progress_bar.setValue(0)
    
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
        
        # 현재 폴더가 있으면 마지막 사용 디렉토리로 저장
        current_folder = self.file_tree_controller.get_current_folder()
        if current_folder:
            self.settings_manager.set_setting('last_directory', str(current_folder))
            self.settings_manager.save_settings()
            logger.info(f"종료 시 마지막 사용 디렉토리 저장: {current_folder}")
        
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
    
    def _on_selection_changed(self, files_count, dirs_count, checked_items_set):
        """
        파일 선택 변경 시 호출되는 슬롯
        
        Args:
            files_count: 선택된 파일 수
            dirs_count: 선택된 폴더 수
            checked_items_set: 체크된 아이템 경로 Set
        """
        logger.info(f"선택 변경: 파일 {files_count}개, 폴더 {dirs_count}개")
        
        # 복사 버튼 상태 업데이트 - 즉시 진행하여 UI 응답성 유지
        has_items = len(checked_items_set) > 0
        self.right_panel.set_buttons_enabled(has_items, has_items)
        
        if not has_items:
            # 선택 항목 없을 때 UI 리셋 - 즉시 진행
            self.right_panel.update_selection_info("0", "0")
            self.progress_bar.setValue(0)
            return
            
        # 토큰 계산 요청은 UI 스레드와 분리하여 지연 실행
        # 이렇게 하면 연속 클릭 시에도 UI가 즉시 반응함
        QTimer.singleShot(0, lambda checked_set=checked_items_set, count=files_count: 
            self.token_controller.calculate_tokens(checked_set, count)
        )
    
    def _on_model_updated(self, model):
        """
        모델 업데이트 이벤트 처리
        
        Args:
            model: 업데이트된 모델
        """
        # 트리 모델을 좌측 패널에 설정
        self.left_panel.set_tree_model(model)
        
        # 트리 뷰에 컨트롤러 참조 설정
        tree_view = self.left_panel.get_tree_view()
        if hasattr(tree_view, 'set_controller'):
            tree_view.set_controller(self.file_tree_controller)
        
        # 트리 뷰 모델 변경 후에는 트리 뷰 스크롤 위치 초기화
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
    
    def _clear_selection(self):
        """모든 체크 항목 선택 해제"""
        logger.info("모든 선택 해제")
        self.file_tree_controller.clear_selection()
        # UI 업데이트는 selection_changed_signal 핸들러에서 처리됨
    