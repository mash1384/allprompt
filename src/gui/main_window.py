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
    QLineEdit, QComboBox, QStyledItemDelegate, QProxyStyle, QStyleOptionViewItem
)
from PySide6.QtCore import Qt, QSize, QDir, Signal, Slot, QThread, QSortFilterProxyModel, QModelIndex, QEvent, QObject, QRect
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction, QFont, QDesktopServices, QPainter, QCursor

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

class CheckableItemDelegate(QStyledItemDelegate):
    """
    체크박스 아이템을 위한 커스텀 델리게이트
    체크박스 영역 클릭 시에만 체크박스 상태를 변경합니다.
    """
    def editorEvent(self, event, model, option, index):
        # 체크박스 클릭 이벤트만 처리 (마우스 릴리즈)
        if event.type() != QEvent.MouseButtonRelease or not index.isValid():
            return super().editorEvent(event, model, option, index)
            
        # 항목이 체크 가능한지 확인
        item = model.itemFromIndex(index)
        if not item or not item.isCheckable() or not item.isEnabled():
            return super().editorEvent(event, model, option, index)
        
        # 클릭된 위치가 체크박스 영역인지 확인
        mouse_pos = event.pos()
        
        # 체크박스 영역 계산 - QStyleOptionViewItem 상세 초기화
        style = option.widget.style() if option.widget else QApplication.style()
        
        # QStyleOptionViewItem 상세 설정
        opt = QStyleOptionViewItem(option)
        
        # 아이템 상태 설정
        if option.widget and option.widget.isEnabled():
            opt.state |= QStyle.State_Enabled
        if index == option.widget.currentIndex():
            opt.state |= QStyle.State_HasFocus
        
        # 체크 상태 설정
        check_state = model.data(index, Qt.CheckStateRole)
        if check_state == Qt.Checked:
            opt.state |= QStyle.State_On
        elif check_state == Qt.PartiallyChecked:
            opt.state |= QStyle.State_NoChange
        else:
            opt.state |= QStyle.State_Off
            
        # 체크박스, 아이콘, 텍스트 features 설정
        if model.data(index, Qt.CheckStateRole) is not None:
            opt.features |= QStyleOptionViewItem.HasCheckIndicator
        
        if model.data(index, Qt.DecorationRole) is not None:
            opt.features |= QStyleOptionViewItem.HasDecoration
            
        if model.data(index, Qt.DisplayRole) is not None:
            opt.features |= QStyleOptionViewItem.HasDisplay
        
        # 체크박스 영역 계산
        check_rect = style.subElementRect(QStyle.SE_ItemViewItemCheckIndicator, opt, option.widget)
        
        # 체크박스 영역이 유효하지 않은 경우 대체 로직
        if check_rect.width() <= 0 or check_rect.x() < 0:
            # 기본 지표 값 얻기
            indicator_width = style.pixelMetric(QStyle.PM_IndicatorWidth, opt, option.widget)
            indicator_height = style.pixelMetric(QStyle.PM_IndicatorHeight, opt, option.widget)
            left_margin = style.pixelMetric(QStyle.PM_LayoutLeftMargin, opt, option.widget)
            
            # X 좌표 계산 (간단한 계산)
            x_pos = option.rect.x() + left_margin
            
            # Y 좌표 계산 (중앙 정렬, 단순화된 버전)
            y_pos = option.rect.y() + (option.rect.height() - indicator_height) // 2
            
            # 체크박스 영역 계산
            check_rect = QRect(
                x_pos,
                y_pos,
                indicator_width,
                indicator_height
            )
        
        # 체크박스 영역 클릭 여부 확인
        is_checkbox_clicked = check_rect.contains(mouse_pos)
        
        if is_checkbox_clicked:
            # 현재 체크 상태 가져오기
            current_state = model.data(index, Qt.CheckStateRole)
            
            # 체크 상태 토글
            if current_state == Qt.Checked:
                new_state = Qt.Unchecked
            else:
                new_state = Qt.Checked
                
            # 모델에 체크 상태 설정
            model.setData(index, new_state, Qt.CheckStateRole)
            
            # 이벤트 소비(consume)하고 이벤트 전파 중지
            event.accept()
            return True
            
        # 체크박스 영역 외부 클릭은 이벤트 전달
        return False

class CustomTreeView(QTreeView):
    """
    커스텀 트리 뷰 클래스
    체크박스 클릭 시 폴더 접기/펼치기가 발생하지 않도록 마우스 이벤트를 직접 제어합니다.
    """
    # 체크박스 클릭 시그널 정의
    checkbox_clicked = Signal(QModelIndex)
    # 항목 클릭 시그널 정의 (체크박스 외부 클릭)
    item_clicked = Signal(QModelIndex)
    
    def __init__(self, parent=None):
        """커스텀 트리 뷰 초기화"""
        super().__init__(parent)
        # 클릭 위치 저장 변수
        self._press_pos = None
        # 체크박스 클릭 진행 중 플래그
        self._checkbox_click_in_progress = False
    
    def mousePressEvent(self, event):
        """마우스 누름 이벤트 처리"""
        # 클릭 위치 저장
        self._press_pos = event.pos()
        index = self.indexAt(event.pos())
        
        if index.isValid():
            # 체크박스 영역 확인
            is_checkbox_click = self._is_checkbox_area(index, event.pos())
            
            if is_checkbox_click:
                # 체크박스 클릭 진행 중 플래그 설정
                self._checkbox_click_in_progress = True
            
            # 체크박스 영역 클릭 여부와 관계없이 기본 마우스 이벤트 처리
            super().mousePressEvent(event)
        else:
            # 유효하지 않은 인덱스에 대한 클릭은 기본 처리
            super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """마우스 놓음 이벤트 처리"""
        index = self.indexAt(event.pos())
        
        if not index.isValid():
            # 유효하지 않은 인덱스에 대한 클릭은 기본 처리
            super().mouseReleaseEvent(event)
            return
            
        # 브랜치 인디케이터 영역 클릭 확인
        if self._is_branch_indicator_area(index, event.pos()):
            # 모델에서 해당 항목이 디렉토리인지 확인
            model = self.model()
            if model:
                item = model.itemFromIndex(index)
                if item and item.data(Qt.UserRole):  # 디렉토리인 경우
                    # 폴더 확장/축소 수동 처리
                    if self.isExpanded(index):
                        self.collapse(index)
                    else:
                        self.expand(index)
                    # 이벤트 소비
                    event.accept()
                    return
            
        # 체크박스 클릭 진행 중이었는지 확인
        if self._checkbox_click_in_progress:
            # 체크박스 클릭 영역에서 마우스를 놓았는지 확인
            if self._is_checkbox_area(index, event.pos()):
                # 체크박스 클릭 완료 - 기본 처리 호출 (체크박스 상태 변경)
                super().mouseReleaseEvent(event)
                
                # 체크박스 클릭 시그널 발생
                self.checkbox_clicked.emit(index)
                
                # 체크박스 클릭 플래그 초기화
                self._checkbox_click_in_progress = False
                
                # 이벤트 소비
                event.accept()
                return
                
        # 체크박스 클릭이 아닌 일반 아이템 영역 클릭 처리
        self._checkbox_click_in_progress = False
        
        # 기본 마우스 릴리스 이벤트 처리
        super().mouseReleaseEvent(event)
        
        # 클릭 완료 후 처리 (체크박스 외부 클릭)
        if self._press_pos is not None:
            # 시작 위치와 종료 위치가 동일한 영역인지 확인 (드래그 방지)
            start_index = self.indexAt(self._press_pos)
            if start_index == index and not self._is_checkbox_area(index, event.pos()):
                model = self.model()
                if model:
                    item = model.itemFromIndex(index)
                    if not (item and item.data(Qt.UserRole)):  # 파일인 경우만
                        # 일반 아이템 영역 클릭 시그널 발생 (파일만)
                        self.item_clicked.emit(index)
    
    def mouseDoubleClickEvent(self, event):
        """더블 클릭 이벤트 처리"""
        # 더블 클릭은 무시하고 이벤트 소비 (기본 확장/축소 방지)
        event.accept()
    
    # QTreeView의 기본 클릭 처리 방지
    def keyPressEvent(self, event):
        """키 입력 이벤트 처리"""
        # 확장/축소와 관련된 키는 직접 처리 
        # (Enter, Return, Right, Left 등의 키)
        key = event.key()
        current_index = self.currentIndex()
        
        if current_index.isValid():
            # 모델에서 현재 항목이 디렉토리인지 확인
            model = self.model()
            if model:
                item = model.itemFromIndex(current_index)
                is_directory = item and item.data(Qt.UserRole)
                
                if key in (Qt.Key_Right, Qt.Key_Enter, Qt.Key_Return):
                    # 폴더인 경우에만 확장 처리
                    if is_directory:
                        if not self.isExpanded(current_index):
                            self.expand(current_index)
                            event.accept()
                            return
                    # 폴더가 아닌 경우 Enter/Return은 항목 클릭으로 처리
                    elif key in (Qt.Key_Enter, Qt.Key_Return):
                        self.item_clicked.emit(current_index)
                        event.accept()
                        return
                elif key == Qt.Key_Left:
                    # 폴더인 경우에만 축소 처리
                    if is_directory:
                        if self.isExpanded(current_index):
                            self.collapse(current_index)
                            event.accept()
                            return
        
        # 나머지 키 이벤트는 기본 처리
        super().keyPressEvent(event)
    
    def _is_checkbox_area(self, index, pos):
        """
        지정된 위치가 체크박스 영역인지 확인
        
        Args:
            index: 항목 인덱스
            pos: 마우스 위치
            
        Returns:
            체크박스 영역이면 True, 아니면 False
        """
        model = self.model()
        if not model:
            return False
            
        # 체크 역할 데이터가 있는지 확인
        if not model.data(index, Qt.CheckStateRole):
            return False
            
        # 항목 시각적 영역
        item_rect = self.visualRect(index)
        
        # QStyleOptionViewItem 설정
        option = QStyleOptionViewItem()
        option.initFrom(self)
        option.rect = item_rect
        
        # 아이템 상태 설정
        if self.isEnabled():
            option.state |= QStyle.State_Enabled
        if self.currentIndex() == index:
            option.state |= QStyle.State_HasFocus
        
        # 체크 상태 설정
        check_state = model.data(index, Qt.CheckStateRole)
        if check_state == Qt.Checked:
            option.state |= QStyle.State_On
        elif check_state == Qt.PartiallyChecked:
            option.state |= QStyle.State_NoChange
        else:
            option.state |= QStyle.State_Off
        
        # 체크박스 특성 설정
        option.features |= QStyleOptionViewItem.HasCheckIndicator
        
        # 데코레이션 특성 설정
        if model.data(index, Qt.DecorationRole):
            option.features |= QStyleOptionViewItem.HasDecoration
        
        # 표시 특성 설정
        if model.data(index, Qt.DisplayRole):
            option.features |= QStyleOptionViewItem.HasDisplay
        
        # 스타일 가져오기
        style = self.style()
        
        # 체크박스 영역 계산
        check_rect = style.subElementRect(QStyle.SE_ItemViewItemCheckIndicator, option, self)
        
        # 유효하지 않은 체크박스 영역인 경우 대체 계산
        if check_rect.width() <= 0 or check_rect.height() <= 0:
            # 기본 지표 값 사용
            indicator_width = style.pixelMetric(QStyle.PM_IndicatorWidth, option, self)
            indicator_height = style.pixelMetric(QStyle.PM_IndicatorHeight, option, self)
            
            # 체크박스 X 위치는 항목 시작 부분 + 약간의 여백
            check_x = item_rect.x() + style.pixelMetric(QStyle.PM_LayoutLeftMargin)
            
            # 체크박스 Y 위치는 항목 중앙에 맞춤
            check_y = item_rect.y() + (item_rect.height() - indicator_height) // 2
            
            # 체크박스 영역 생성
            check_rect = QRect(check_x, check_y, indicator_width, indicator_height)
            
            # 체크박스 영역 좀 더 확장 (클릭 감지 향상)
            check_rect.adjust(-2, -2, 2, 2)
        
        # 마우스 위치가 체크박스 영역 내에 있는지 확인
        return check_rect.contains(pos)
    
    def _is_branch_indicator_area(self, index, pos):
        """
        지정된 위치가 브랜치 인디케이터(폴더 확장/축소 아이콘) 영역인지 확인
        
        Args:
            index: 항목 인덱스
            pos: 마우스 위치
            
        Returns:
            브랜치 인디케이터 영역이면 True, 아니면 False
        """
        # 항목 시각적 영역
        rect = self.visualRect(index)
        
        # 브랜치 인디케이터 위치는 항목 앞쪽에 있음
        left_margin = self.indentation()
        
        # 항목의 깊이
        depth = 0
        parent = index.parent()
        while parent.isValid():
            depth += 1
            parent = parent.parent()
        
        # 항목 들여쓰기까지의 영역이 브랜치 인디케이터 영역
        branch_rect_width = depth * left_margin
        branch_rect = QRect(rect.x() - branch_rect_width, rect.y(), 
                          branch_rect_width, rect.height())
        
        # 마우스 위치가 브랜치 인디케이터 영역 내에 있는지 확인
        return branch_rect.contains(pos)

class MainWindow(QMainWindow):
    """메인 애플리케이션 윈도우"""
    
    def __init__(self):
        """Initialize the main window"""
        super().__init__()
        
        self.setWindowTitle("LLM Prompt Helper")
        
        # Initialize progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # Initialize selection tracking
        self.checked_items = set()  # Paths of checked items
        self.checked_files = 0      # Number of checked files
        self.checked_dirs = 0       # Number of checked directories
        
        # Initialize folder state
        self.current_folder = None  # Current directory
        self.gitignore_filter = None  # .gitignore filter
        self.show_hidden = False  # Hidden files display
        
        # Initialize tokenizer
        self.tokenizer = Tokenizer()  # Default tokenizer
        
        # Initialize caches
        self.token_cache = {}  # Cache for token counts {file_path: token_count}
        self.file_cache = {}   # Cache for file contents {file_path: content}
        self.total_tokens = 0  # Total token count for selected files
        
        # Initialize token calculation thread
        self.token_thread = None
        
        # Initialize icons
        self._init_icons()
        
        # Initialize UI components
        self._init_ui()
        
        # Center the window on screen
        self._center_window()
        
        logger.info("Main window initialized")
        
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
        Initialize UI components
        """
        # Central widget setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Modern style sheet
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1E1E1E;
                color: #E0E0E0;
            }
            
            QLabel {
                color: #E0E0E0;
            }
            
            QLabel[infoLabel="true"] {
                color: #BBBBBB;
                font-size: 14px;
            }
            
            QLabel[infoValue="true"] {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
            }
            
            QLabel#panelHeader {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 0px;
                border-bottom: 1px solid #3C3C3C;
                margin-bottom: 8px;
            }
            
            QLabel#pathLabel {
                color: #BBBBBB;
                background-color: #2A2A2A;
                border-radius: 4px;
                padding: 4px 8px;
            }
            
            QPushButton {
                background-color: #2D2D30;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #3E3E42;
            }
            
            QPushButton:pressed {
                background-color: #1E1E1E;
            }
            
            QPushButton:disabled {
                background-color: #2D2D30;
                color: #6D6D6D;
            }
            
            QPushButton#openFolderButton, QPushButton#copyButton, QPushButton#clearButton {
                background-color: transparent;
                border: 1px solid #555555;
                font-size: 14px;
                color: #DDDDDD;
                text-align: left;
                padding-left: 36px;
            }
            
            QPushButton#openFolderButton:hover, QPushButton#copyButton:hover, QPushButton#clearButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid #777777;
            }
            
            QPushButton#openFolderButton:pressed, QPushButton#copyButton:pressed, QPushButton#clearButton:pressed {
                background-color: rgba(0, 0, 0, 0.1);
            }
            
            QTreeView {
                background-color: #252526;
                alternate-background-color: #2D2D30;
                border: 1px solid #3C3C3C;
                border-radius: 6px;
                padding: 4px;
                selection-background-color: #264F78;
            }
            
            QTreeView::item {
                padding: 4px;
                border-radius: 4px;
            }
            
            /* QTreeView::item:hover {
                background-color: #2A2D2E;
                border: 1px solid #3C3C3C;
            } */
            
            QTreeView::item:selected {
                background-color: #264F78;
            }
            
            QScrollBar:vertical {
                border: none;
                background: #2A2A2A;
                width: 10px;
                border-radius: 5px;
            }
            
            QScrollBar::handle:vertical {
                background: #5A5A5A;
                min-height: 20px;
                border-radius: 5px;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QScrollBar:horizontal {
                border: none;
                background: #2A2A2A;
                height: 10px;
                border-radius: 5px;
            }
            
            QScrollBar::handle:horizontal {
                background: #5A5A5A;
                min-width: 20px;
                border-radius: 5px;
            }
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            
            QSplitter::handle {
                background-color: #3C3C3C;
            }
            
            QStatusBar {
                background-color: #2D2D30;
                color: #BBBBBB;
            }
            
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #333333;
                text-align: center;
                color: white;
            }
            
            QProgressBar::chunk {
                background-color: #007ACC;
                border-radius: 4px;
            }
            
            QMenu {
                background-color: #2D2D30;
                border: 1px solid #3C3C3C;
            }
            
            QMenu::item {
                padding: 6px 25px 6px 25px;
                color: #CCCCCC;
            }
            
            QMenu::item:selected {
                background-color: #3E3E42;
                color: #FFFFFF;
            }
            
            QMenuBar {
                background-color: #2D2D30;
                color: #CCCCCC;
            }
            
            QMenuBar::item {
                padding: 6px 10px;
                background: transparent;
            }
            
            QMenuBar::item:selected {
                background-color: #3E3E42;
                color: #FFFFFF;
            }
        """)
        
        # Main layout (vertical)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)  # Layout element spacing
        
        # Left-right panel splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)  # Splitter handle width
        splitter.setChildrenCollapsible(False)  # Prevent children from being fully collapsed
        
        # ===== Left Panel (File Tree View) =====
        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(10, 10, 10, 10)
        
        # Size policy setup (horizontal/vertical expansion)
        left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Files/folders header label
        files_header = QLabel("Files/Folders")
        files_header.setObjectName("panelHeader")
        left_panel_layout.addWidget(files_header)
        
        # File tree view - using custom tree view
        self.tree_view = CustomTreeView()
        self.tree_view.setSelectionMode(QTreeView.NoSelection)
        self.tree_view.setAlternatingRowColors(False)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.header().setVisible(False)
        self.tree_view.setTextElideMode(Qt.ElideMiddle)
        self.tree_view.setAttribute(Qt.WA_MacShowFocusRect, False)  # Remove macOS focus rectangle
        self.tree_view.setFocusPolicy(Qt.NoFocus)  # Remove focus effects
        self.tree_view.setMouseTracking(True)  # Enable mouse tracking (for hover effects)
        
        # Prevent editing by double-click
        self.tree_view.setEditTriggers(QTreeView.NoEditTriggers)
        
        # Allow mouse event propagation
        self.tree_view.setAttribute(Qt.WA_NoMousePropagation, False)
        
        # Using custom signals instead of the default clicked signal
        self.tree_view.item_clicked.connect(self._on_item_clicked)
        
        # Tree view size policy setup (horizontal/vertical expansion)
        self.tree_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Create tree view item model
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Files/Folders"])
        self.tree_view.setModel(self.tree_model)
        
        # Connect tree view events
        self.tree_model.itemChanged.connect(self._on_item_changed)
        
        # Set custom delegate (for checkbox styling)
        self.checkable_delegate = CheckableItemDelegate()
        self.tree_view.setItemDelegate(self.checkable_delegate)
        
        # Connect folder expansion/collapse events
        self.tree_view.expanded.connect(self._on_item_expanded)
        self.tree_view.collapsed.connect(self._on_item_collapsed)
        
        left_panel_layout.addWidget(self.tree_view)
        
        # ===== Right Panel (Info and Actions) =====
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(10, 10, 10, 10)
        
        # Size policy setup (fixed horizontal, expanding vertical)
        right_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # Folder selection group
        folder_header = QLabel("Folder Selection")
        folder_header.setObjectName("panelHeader")
        right_panel_layout.addWidget(folder_header)
        
        # Folder open button and path layout
        folder_group = QWidget()
        folder_layout = QVBoxLayout(folder_group)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(10)  # Add spacing between elements
        
        # Open folder button
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.setObjectName("openFolderButton")
        self.open_folder_button.setIcon(self.folder_icon)
        self.open_folder_button.clicked.connect(self._open_folder_dialog)
        # Button size policy setup - fill width
        self.open_folder_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.open_folder_button.setMinimumHeight(40)  # Increase button height
        folder_layout.addWidget(self.open_folder_button)
        
        # 현재 폴더 경로를 표시할 수평 레이아웃 생성
        current_folder_hbox_layout = QHBoxLayout()
        current_folder_hbox_layout.setContentsMargins(0, 4, 0, 0)
        
        # Current folder path label
        folder_path_label = QLabel("Current folder:")
        folder_path_label.setProperty("infoLabel", True)
        folder_path_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        current_folder_hbox_layout.addWidget(folder_path_label)
        
        self.folder_path = QLabel("No folder selected")
        self.folder_path.setObjectName("pathLabel")
        self.folder_path.setWordWrap(True)
        self.folder_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # Path label size policy setup (horizontal expansion)
        self.folder_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        current_folder_hbox_layout.addWidget(self.folder_path)
        
        # 수평 레이아웃을 수직 레이아웃에 추가
        folder_layout.addLayout(current_folder_hbox_layout)
        
        right_panel_layout.addWidget(folder_group)
        
        # Selection info group
        info_header = QLabel("Selection Info")
        info_header.setObjectName("panelHeader")
        right_panel_layout.addWidget(info_header)
        
        # Info display container improvement
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(12)  # Increase info item spacing
        
        info_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Selected file count
        file_count_group = QWidget()
        file_count_layout = QHBoxLayout(file_count_group)
        file_count_layout.setContentsMargins(0, 4, 0, 4)
        
        selected_files_label = QLabel("Selected files:")
        selected_files_label.setProperty("infoLabel", True)
        selected_files_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        file_count_layout.addWidget(selected_files_label)
        
        file_count_layout.addStretch(1)  # Add stretch to align value to the right
        
        self.selected_files_count = QLabel("0")
        self.selected_files_count.setProperty("infoValue", True)
        self.selected_files_count.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)  # Minimum size
        self.selected_files_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # Right align text
        file_count_layout.addWidget(self.selected_files_count)
        
        info_layout.addWidget(file_count_group)
        
        # Total token count
        token_count_group = QWidget()
        token_count_layout = QHBoxLayout(token_count_group)
        token_count_layout.setContentsMargins(0, 4, 0, 4)
        
        total_tokens_label = QLabel("Total tokens:")
        total_tokens_label.setProperty("infoLabel", True)
        total_tokens_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        token_count_layout.addWidget(total_tokens_label)
        
        token_count_layout.addStretch(1)  # Add stretch to align value to the right
        
        self.total_tokens_count = QLabel("0")
        self.total_tokens_count.setProperty("infoValue", True)
        self.total_tokens_count.setObjectName("total_tokens_count")  # ID 변경
        self.total_tokens_count.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)  # Minimum size
        self.total_tokens_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # Right align text
        token_count_layout.addWidget(self.total_tokens_count)
        
        info_layout.addWidget(token_count_group)
        
        right_panel_layout.addWidget(info_container)
        
        # Action button group
        action_header = QLabel("Actions")
        action_header.setObjectName("panelHeader")
        right_panel_layout.addWidget(action_header)
        
        # Action button container
        action_container = QWidget()
        action_layout = QVBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)  # Add spacing between buttons
        
        # Copy to clipboard button
        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.setObjectName("copyButton")
        # Use a simple document icon for copy button
        self.copy_button.setIcon(self.copy_icon)
        # Icon setup
        self.copy_button.setIconSize(QSize(20, 20))
        self.copy_button.setLayoutDirection(Qt.LeftToRight)
        self.copy_button.clicked.connect(self._copy_to_clipboard)
        self.copy_button.setEnabled(False)  # Initially disabled
        # Copy button size policy
        self.copy_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.copy_button.setMinimumHeight(44)
        action_layout.addWidget(self.copy_button)
        
        # Clear selection button
        self.clear_button = QPushButton("Clear Selection")
        self.clear_button.setObjectName("clearButton")
        # Use a simple X icon for clear button
        self.clear_button.setIcon(self.clear_icon)
        self.clear_button.setIconSize(QSize(20, 20))
        self.clear_button.setLayoutDirection(Qt.LeftToRight)
        self.clear_button.clicked.connect(self._clear_selection)
        self.clear_button.setEnabled(False)  # Initially disabled
        self.clear_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.clear_button.setMinimumHeight(44)
        action_layout.addWidget(self.clear_button)
        
        right_panel_layout.addWidget(action_container)
        
        # Add margin (bottom margin)
        right_panel_layout.addStretch()
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set window minimum size (more spacious)
        self.setMinimumSize(1000, 700)
        
        # Set splitter initial size ratio (left:right = 7:3)
        splitter.setSizes([700, 300])
        
        # Splitter size policy setup
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Create status bar
        status_bar = QStatusBar()
        status_bar.setFixedHeight(24)  # Set a fixed height for the status bar
        self.setStatusBar(status_bar)
        
        # Status message label
        self.status_label = QLabel("Ready")
        status_bar.addWidget(self.status_label, 1)
        
        # Add progress bar
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        status_bar.addPermanentWidget(self.progress_bar)
        
        # Create menu bar
        self._create_menu()
        
        # Window size and title
        self.setWindowTitle("LLM Prompt Helper")
        self.resize(1200, 800)  # Initial window size
        
        # Window icon
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_FileDialogInfoView))
        
        # Status bar initial message
        self.statusBar().showMessage("Ready", 3000)
        
        # Center window on screen
        self._center_window()
        
        # Log UI initialization
        logger.info("UI initialized")
    
    def _create_menu(self):
        """Create menu bar"""
        menubar = QMenuBar()
        self.setMenuBar(menubar)
        
        # File menu
        file_menu = QMenu("File", self)
        menubar.addMenu(file_menu)
        
        # Open folder action
        open_folder_action = QAction("Open Folder", self)
        open_folder_action.setShortcut("Ctrl+O")
        open_folder_action.triggered.connect(self._open_folder_dialog)
        file_menu.addAction(open_folder_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = QMenu("Help", self)
        menubar.addMenu(help_menu)
        
        # About action
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)
    
    def _open_folder_dialog(self):
        """Display folder selection dialog"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            str(Path.home()),
            QFileDialog.ShowDirsOnly
        )
        
        if folder_path:
            self._load_folder(folder_path)
    
    def _load_folder(self, folder_path: str):
        """
        Load the specified folder path and display in tree view
        
        Args:
            folder_path: Folder path to load
        """
        try:
            self.current_folder = Path(folder_path)
            
            # Stop existing tokenizer thread if running
            if self.token_thread and self.token_thread.isRunning():
                self.token_thread.stop()
                self.token_thread.wait()
            
            # Reset state
            self.checked_items.clear()
            self.checked_files = 0
            self.checked_dirs = 0
            self.total_tokens = 0
            self.token_cache.clear()
            self.file_cache.clear()
            
            # Update UI
            self.folder_path.setText(folder_path)
            self.selected_files_count.setText("0")
            self.total_tokens_count.setText("0")
            self.copy_button.setEnabled(False)
            
            # Initialize .gitignore filter
            self.gitignore_filter = GitignoreFilter(folder_path)
            if self.gitignore_filter.has_gitignore():
                self.statusBar().showMessage(f"Applying .gitignore rules: {self.gitignore_filter.get_gitignore_path()}", 5000)
            else:
                self.statusBar().showMessage("No .gitignore file found. All files will be displayed.", 5000)
                self.gitignore_filter = None
                
            # Scan files and folders
            include_hidden = False  # Always hide hidden files
            items = scan_directory(folder_path, follow_symlinks=False, include_hidden=include_hidden)
            
            # Apply .gitignore filtering
            if self.gitignore_filter:
                filtered_items = []
                ignored_count = 0
                
                for item in items:
                    path = item['path']
                    # Always include the root directory itself
                    if path == self.current_folder:
                        filtered_items.append(item)
                        continue
                        
                    # Apply .gitignore rules
                    if self.gitignore_filter.should_ignore(path):
                        ignored_count += 1
                        continue
                    
                    filtered_items.append(item)
                
                items = filtered_items
                
                if ignored_count > 0:
                    self.statusBar().showMessage(f"{ignored_count} items filtered by .gitignore rules.", 5000)
            
            # Filter venv folders
            venv_count = 0
            filtered_items = []
            
            for item in items:
                path = item['path']
                rel_path = item.get('rel_path', '')
                parts = Path(rel_path).parts
                
                # Always include the root directory itself
                if path == self.current_folder:
                    filtered_items.append(item)
                    continue
                
                # Exclude venv, virtualenv, env, etc. virtual environment folders
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
                self.statusBar().showMessage(f"{venv_count} virtual environment folders filtered.", 5000)
            
            # Apply sorting - sort the entire list of items first
            items = sort_items(items)
            logger.info(f"Sorting completed: {len(items)} items sorted by folders first, then by name")
            
            # Initialize tree view model and populate
            self.tree_model.clear()
            self.tree_model.setHorizontalHeaderLabels(['Files/Folders'])
            
            # Add items to tree view
            self._populate_tree_view(items)
            
            # Collect all file paths as a list
            text_files = []
            for item in items:
                path = item.get('path')
                is_dir = item.get('is_dir')
                error = item.get('error')
                
                # Exclude directories or items with errors
                if is_dir or error:
                    continue
                
                # Add only text files
                if not is_binary_file(path):
                    text_files.append(path)
            
            # Start token calculation in background
            self._start_token_calculation(text_files)
            
            logger.info(f"Folder loaded: {folder_path}")
            
        except Exception as e:
            logger.error(f"Error loading folder: {e}")
            self.statusBar().showMessage(f"Error: {str(e)}", 5000)
    
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
        트리 아이템 체크 상태 변경 시 호출되는 슬롯
        모든 체크 상태 변경 로직을 중앙화하여 처리합니다.
        """
        if not self.current_folder or not item.isCheckable():
            return
        
        # 체크 상태가 변경된 경우에만 처리
        checked = item.checkState() == Qt.Checked
        item_path = self._get_item_path(item)
        
        if not item_path:
            return
        
        # 이벤트 처리 중 플래그 설정
        if hasattr(self, '_processing_check_event') and self._processing_check_event:
            return
        
        self._processing_check_event = True
        
        try:
            # 일시적으로 모델 시그널 연결 해제
            self.tree_model.itemChanged.disconnect(self._on_item_changed)
            
            # 1. 현재 아이템 상태 업데이트
            path_str = str(item_path)
            is_dir = item_path.is_dir()
            
            if checked:
                self.checked_items.add(path_str)
            else:
                self.checked_items.discard(path_str)
            
            # 2. 폴더인 경우 하위 항목도 같은 상태로 설정
            if is_dir:
                self._set_item_checked_state(item, checked)
            
            # 3. 부모 폴더의 체크 상태 업데이트
            self._update_parent_checked_state(item)
            
            # 4. 체크 통계 업데이트 (파일/폴더 카운트)
            self._update_check_stats()
            
            # 5. 토큰 수 업데이트
            self._update_token_count()
        finally:
            # 모델 시그널 다시 연결
            self.tree_model.itemChanged.connect(self._on_item_changed)
            self._processing_check_event = False
    
    def _set_item_checked_state(self, item, checked):
        """
        아이템과 모든 자식 아이템의 체크 상태를 설정
        중복 계산 방지 로직 추가
        """
        # 현재 상태와 설정할 상태를 비교하여 변경이 필요한 경우에만 처리
        current_state = item.checkState()
        target_state = Qt.Checked if checked else Qt.Unchecked
        
        if current_state != target_state:
            # 현재 아이템의 체크 상태 설정
            item.setCheckState(target_state)
            
            # 아이템 경로 업데이트
            item_path = self._get_item_path(item)
            if item_path:
                path_str = str(item_path)
                if checked:
                    self.checked_items.add(path_str)
                else:
                    self.checked_items.discard(path_str)
        
        # 모든 자식 아이템 처리 - 상태와 무관하게 모든 자식 처리
        row_count = item.rowCount()
        for row in range(row_count):
            child_item = item.child(row)
            if child_item and child_item.isCheckable() and child_item.isEnabled():
                self._set_item_checked_state(child_item, checked)
    
    def _update_parent_checked_state(self, item):
        """
        부모 아이템의 체크 상태를 자식 아이템들의 상태 기준으로 업데이트
        불필요한 재귀 호출 방지 로직 추가
        """
        parent = item.parent()
        if not parent:
            return  # 루트 아이템이면 패스
        
        # 부모의 모든 자식 상태 확인
        all_checked = True
        any_checked = False
        has_children = False
        
        row_count = parent.rowCount()
        for row in range(row_count):
            child = parent.child(row)
            if child and child.isCheckable() and child.isEnabled():
                has_children = True
                if child.checkState() == Qt.Checked:
                    any_checked = True
                else:
                    all_checked = False
                
                if any_checked and not all_checked:
                    break  # 조기 종료
        
        # 자식이 없는 경우 처리
        if not has_children:
            return
            
        # 부모 상태 결정
        new_state = Qt.Checked if all_checked else (Qt.PartiallyChecked if any_checked else Qt.Unchecked)
        
        # 현재 상태와 새 상태 비교
        current_state = parent.checkState()
        
        if current_state != new_state:
            # 부모 상태 업데이트
            parent.setCheckState(new_state)
            
            # 부모 경로 업데이트 (완전 체크된 경우만)
            parent_path = self._get_item_path(parent)
            if parent_path:
                path_str = str(parent_path)
                if new_state == Qt.Checked:
                    self.checked_items.add(path_str)
                else:
                    self.checked_items.discard(path_str)
            
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
        self.statusBar().showMessage(f"Calculating tokens: 0/{len(files)} files", 0)
        
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
        """Update progress bar when token calculation progresses"""
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.progress_bar.setVisible(True)
        
        # Update status message
        self.statusBar().showMessage(f"Calculating tokens: {current}/{total}", 0)
    
    def _on_token_calculated(self, file_path: str, token_count: int):
        """Callback when token count is calculated for a file"""
        # Add to token cache
        self.token_cache[file_path] = token_count
        
        # Update progress bar value for each file
        current = self.progress_bar.value() + 1
        total = self.progress_bar.maximum()
        self.progress_bar.setValue(current)
        
        # Update status message
        self.statusBar().showMessage(f"Calculating tokens: {current}/{total}", 0)
    
    def _on_token_calculation_finished(self):
        """Callback when token calculation is complete"""
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        # Update status message
        self.statusBar().showMessage("Token calculation complete", 5000)
        
        # Update token count display
        self._update_token_count()
    
    def _on_token_calculation_error(self, error_msg: str):
        """Handle token calculation errors"""
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        # Update status message
        self.statusBar().showMessage(f"Token calculation error: {error_msg}", 5000)
        logger.error(f"Token calculation error: {error_msg}")
    
    def _update_token_count(self):
        """Update the total token count based on checked files"""
        old_total = self.total_tokens
        self.total_tokens = 0
        
        # Sum up tokens for all checked files
        for path_str in self.checked_items:
            path = Path(path_str)
            # Skip directories
            if path.is_dir():
                continue
                
            # Get token count from cache if available
            if str(path) in self.token_cache:
                self.total_tokens += self.token_cache[str(path)]
        
        # Update UI
        self.total_tokens_count.setText(f"{self.total_tokens:,}")
        
        # Log if changed
        if old_total != self.total_tokens:
            logger.info(f"Total token count updated: {self.total_tokens}")
            
        return self.total_tokens
    
    def _show_about_dialog(self):
        """Show the about dialog"""
        about_text = f"""
        <h2>LLM Prompt Helper</h2>
        <p>Version 1.0.0</p>
        <p>A tool to help prepare code snippets for LLM prompts.</p>
        <p>©2023</p>
        <p>Using tokenizer: {self.tokenizer.model_name}</p>
        """
        
        QMessageBox.about(self, "About", about_text)
    
    def _copy_to_clipboard(self):
        """Copy selected files to clipboard in formatted output"""
        try:
            # Get all checked files
            files = []
            for path_str in sorted(self.checked_items):
                path = Path(path_str)
                # Only include files, not directories
                if not path.is_dir():
                    files.append(path)
            
            if not files:
                self.statusBar().showMessage("No files selected to copy", 5000)
                return
            
            total_files = len(files)
            self.statusBar().showMessage(f"Preparing {total_files} files for clipboard...", 0)
            
            # Update progress bar
            self.progress_bar.setRange(0, total_files)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            
            # Reset token count if needed
            if self.total_tokens <= 0:
                self._update_token_count()
            
            # Generate formatted output
            output = generate_full_output(
                self.current_folder, 
                [str(f) for f in files],
                self.file_cache
            )
            
            # Copy to clipboard
            if copy_to_clipboard(output):
                # Success message
                self.statusBar().showMessage(
                    f"Copied {total_files} files ({self.total_tokens} tokens) to clipboard", 
                    5000
                )
                logger.info(f"Copied {total_files} files ({self.total_tokens} tokens) to clipboard")
            else:
                # Failed message
                self.statusBar().showMessage("Clipboard copy failed", 5000)
                logger.error("Clipboard copy failed")
                
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}", exc_info=True)
            self.statusBar().showMessage(f"Error occurred during copy: {str(e)}", 5000)
            # Show error message box
            error_box = QMessageBox(self)
            error_box.setObjectName("critical")
            error_box.setWindowTitle("Copy Error")
            error_box.setText(f"An error occurred while copying to clipboard.\n\n{str(e)}")
            error_box.setIcon(QMessageBox.Critical)
            error_box.exec()
    
    def _toggle_hidden_files(self):
        """Toggle display of hidden files/folders"""
        self.show_hidden = not self.show_hidden
        if self.current_folder:
            self._load_folder(str(self.current_folder))
    
    def _toggle_gitignore_filter(self):
        """Toggle application of .gitignore filter"""
        if self.current_folder:
            self._load_folder(str(self.current_folder))
    
    def _center_window(self):
        """윈도우를 화면 중앙에 배치"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.geometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)

    def closeEvent(self, event):
        """Handle program exit"""
        # Terminate tokenizer thread
        if self.token_thread and self.token_thread.isRunning():
            self.token_thread.stop()
            self.token_thread.wait()
        
        event.accept()
        
    def _handle_copy_error(self, error_text: str):
        """Handle copy error"""
        logger.error(f"Copy error: {error_text}")
        msg_box = QMessageBox(self)
        msg_box.setObjectName("critical")
        msg_box.setWindowTitle("Error")
        msg_box.setText(f"An error occurred while copying to clipboard:\n{error_text}")
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.exec()

    def _on_item_clicked(self, index):
        """
        트리 뷰 항목 클릭 시 호출되는 슬롯
        - 이 메서드는 파일 항목 클릭 시에만 호출됩니다.
        - CustomTreeView의 mouseReleaseEvent에서 보내는 시그널에 의해 트리거됩니다.
        """
        if not index.isValid():
            return
            
        # 인덱스에서 항목 얻기
        item = self.tree_model.itemFromIndex(index)
        if not item or not item.isEnabled():
            return
        
        # 파일 항목인 경우 체크 상태 토글
        if item.isCheckable() and not item.data(Qt.UserRole):  # 파일 항목인 경우만
            current_state = item.checkState()
            new_state = Qt.Unchecked if current_state == Qt.Checked else Qt.Checked
            item.setCheckState(new_state)
                
        # 참고: 체크박스 상태 변경은 itemChanged 시그널로 처리되어 _on_item_changed 메서드에서 반영됨
    
    def _on_item_double_clicked(self, index):
        """
        트리 뷰 항목 더블클릭 시 호출되는 슬롯 (더이상 사용하지 않음)
        clicked 이벤트로 모든 동작을 처리함
        
        Args:
            index: 더블클릭된 항목의 인덱스
        """
        pass  # 더이상 사용하지 않음
    
    def _update_check_stats(self):
        """checked_items 세트를 기반으로 파일/폴더 카운트 업데이트"""
        self.checked_files = 0
        self.checked_dirs = 0
        
        for path_str in self.checked_items:
            path = Path(path_str)
            if path.is_dir():
                self.checked_dirs += 1
            else:
                self.checked_files += 1
        
        # UI 업데이트
        self.selected_files_count.setText(f"{self.checked_files}")
        self.copy_button.setEnabled(self.checked_files > 0)
        self.clear_button.setEnabled(len(self.checked_items) > 0)
    
    def _find_item_by_path(self, path: Path) -> Optional[QStandardItem]:
        """
        Find tree item corresponding to a path
        
        Args:
            path: File/folder path to find
            
        Returns:
            Found QStandardItem or None
        """
        if not self.current_folder:
            return None
            
        # Calculate relative path
        try:
            rel_path = path.relative_to(self.current_folder)
        except ValueError:
            return None
            
        # Start from root and follow path
        parent_item = self.tree_model.item(0)  # Root item
        if not parent_item:
            return None
            
        # Return root item if no path parts
        if len(rel_path.parts) == 0:
            return parent_item
            
        # Find child item for each path part
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
    
    def _on_item_expanded(self, index):
        """Called when a tree item is expanded"""
        item = self.tree_model.itemFromIndex(index)
        if item and item.data(Qt.UserRole) is True:  # For directories only
            item.setIcon(self.folder_open_icon)
    
    def _on_item_collapsed(self, index):
        """Called when a tree item is collapsed"""
        item = self.tree_model.itemFromIndex(index)
        if item and item.data(Qt.UserRole) is True:  # For directories only
            item.setIcon(self.folder_icon)
    
    def _clear_selection(self):
        """Clear all checked items in the tree view"""
        if not self.tree_model:
            return
            
        # Temporarily disconnect the itemChanged signal to avoid recursion
        self.tree_model.itemChanged.disconnect(self._on_item_changed)
        
        # Clear root item and all children
        root_item = self.tree_model.item(0)
        if root_item:
            self._uncheck_item_recursive(root_item)
            
        # Clear checked items set
        self.checked_items.clear()
        self.checked_files = 0
        self.checked_dirs = 0
        
        # Update UI
        self.selected_files_count.setText("0")
        self.total_tokens_count.setText("0")
        self.total_tokens = 0
        
        # Disable buttons
        self.copy_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        
        # Reconnect the itemChanged signal
        self.tree_model.itemChanged.connect(self._on_item_changed)
        
        # Log
        logger.info("Selection cleared")
        self.statusBar().showMessage("Selection cleared", 3000)
    
    def _uncheck_item_recursive(self, item):
        """Recursively uncheck an item and all its children"""
        if item.isCheckable():
            item.setCheckState(Qt.Unchecked)
            
        # Process children
        for row in range(item.rowCount()):
            child = item.child(row)
            if child:
                self._uncheck_item_recursive(child)
    