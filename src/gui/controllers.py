#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
컨트롤러 모듈
애플리케이션의 로직을 UI와 분리하여 처리하는 컨트롤러 클래스를 정의합니다.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Union, Tuple

from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon

# 코어 모듈 임포트
from src.core.file_scanner import scan_directory, is_binary_file
from src.core.filter import GitignoreFilter
from src.core.sort_utils import sort_items
from src.gui.constants import ITEM_DATA_ROLE

logger = logging.getLogger(__name__)


class FileTreeController(QObject):
    """
    파일 트리 컨트롤러
    파일 시스템 스캔, 트리 모델 관리, 아이템 선택 및 상태 변경 로직을 처리합니다.
    """
    
    # 시그널 정의
    folder_loaded_signal = Signal(list)  # 폴더 로드 완료 시 발생 (items 목록 전달)
    selection_changed_signal = Signal(int, int, set)  # 선택 변경 시 발생 (파일 수, 폴더 수, 체크된 아이템 Set)
    model_updated_signal = Signal(QStandardItemModel)  # 모델 업데이트 시 발생 (업데이트된 모델 전달)
    
    def __init__(self, folder_icon=None, folder_open_icon=None, file_icon=None, code_file_icon=None, 
                 doc_file_icon=None, symlink_icon=None, binary_icon=None, error_icon=None, image_file_icon=None):
        """
        FileTreeController 초기화
        
        Args:
            folder_icon: 폴더 아이콘
            folder_open_icon: 열린 폴더 아이콘
            file_icon: 일반 파일 아이콘
            code_file_icon: 코드 파일 아이콘
            doc_file_icon: 문서 파일 아이콘
            symlink_icon: 심볼릭 링크 아이콘
            binary_icon: 바이너리 파일 아이콘
            error_icon: 오류 아이콘
            image_file_icon: 이미지 파일 아이콘
        """
        super().__init__()
        
        # 아이콘 저장
        self.folder_icon = folder_icon
        self.folder_open_icon = folder_open_icon
        self.file_icon = file_icon
        self.code_file_icon = code_file_icon
        self.doc_file_icon = doc_file_icon
        self.symlink_icon = symlink_icon
        self.binary_icon = binary_icon
        self.error_icon = error_icon
        self.image_file_icon = image_file_icon
        
        # 트리 모델 초기화
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Files/Folders"])
        
        # 파일/폴더 관련 상태 변수
        self.current_folder = None  # 현재 폴더
        self.gitignore_filter = None  # .gitignore 필터
        self.show_hidden = False  # 숨김 파일 표시 여부
        self.apply_gitignore_rules = True  # .gitignore 규칙 적용 여부
        
        # 체크 상태 추적
        self.checked_items = set()  # 체크된 항목 경로 집합
        self.checked_files = 0  # 체크된 파일 수
        self.checked_dirs = 0  # 체크된 폴더 수
        
        # 시그널 연결 플래그
        self._processing_check_event = False
        
        # 트리 모델 시그널 연결
        self.tree_model.itemChanged.connect(self.handle_item_change)
        
    def load_folder(self, folder_path: str):
        """
        지정된 폴더를 로드하고 트리 모델 업데이트
        
        Args:
            folder_path: 로드할 폴더 경로
        """
        try:
            logger.info(f"=== 폴더 로드 시작: {folder_path} ===")
            self.current_folder = Path(folder_path)
            
            # 상태 초기화
            self.checked_items.clear()
            self.checked_files = 0
            self.checked_dirs = 0
            
            # .gitignore 필터 초기화 (필터링이 활성화된 경우만)
            self.gitignore_filter = None
            if self.apply_gitignore_rules:
                self.gitignore_filter = GitignoreFilter(folder_path)
                if not self.gitignore_filter.has_gitignore():
                    self.gitignore_filter = None
                
            # 파일/폴더 스캔
            include_hidden = self.show_hidden
            logger.info(f"폴더 스캔 시작: {folder_path}")
            items = scan_directory(folder_path, follow_symlinks=False, include_hidden=include_hidden)
            logger.info(f"폴더 스캔 완료: {len(items)}개 항목 발견")
            
            # .gitignore 필터링 적용
            if self.gitignore_filter:
                filtered_items = []
                
                for item in items:
                    path = item['path']
                    # 루트 디렉토리는 항상 포함
                    if path == self.current_folder:
                        filtered_items.append(item)
                        continue
                        
                    # .gitignore 규칙 적용
                    if self.gitignore_filter.should_ignore(path):
                        continue
                    
                    filtered_items.append(item)
                
                items = filtered_items
            
            logger.info(f"gitignore 필터링 후: {len(items)}개 항목")
            
            # venv 폴더 필터링
            filtered_items = []
            
            for item in items:
                path = item['path']
                rel_path = item.get('rel_path', '')
                parts = Path(rel_path).parts
                
                # 루트 디렉토리는 항상 포함
                if path == self.current_folder:
                    filtered_items.append(item)
                    continue
                
                # venv, virtualenv, env 등의 가상환경 폴더 제외
                is_venv = False
                for part in parts:
                    if part in ['venv', 'virtualenv', 'env', '.venv'] or part.startswith('venv-'):
                        is_venv = True
                        break
                
                if not is_venv:
                    filtered_items.append(item)
            
            items = filtered_items
            
            logger.info(f"venv 필터링 후: {len(items)}개 항목")
            
            # 정렬 적용
            items = sort_items(items)
            logger.info(f"정렬 완료: {len(items)}개 항목")
            
            # 트리 뷰 모델 업데이트
            self._populate_tree_view(items)
            logger.info("트리 뷰 업데이트 완료")
            
            # 로드 완료 시그널 발생
            self.folder_loaded_signal.emit(items)
            
            logger.info(f"=== 폴더 로드 완료: {folder_path} ===")
            
            return items
            
        except Exception as e:
            logger.error(f"폴더 로드 중 오류: {e}", exc_info=True)
            raise
    
    def _populate_tree_view(self, items: List[Dict[str, Any]]):
        """
        아이템 목록으로 트리 모델 채우기
        
        Args:
            items: 아이템 목록
        """
        # 기존 시그널 연결 해제
        if hasattr(self, '_processing_check_event'):
            self._processing_check_event = True
            try:
                self.tree_model.itemChanged.disconnect(self.handle_item_change)
            except Exception:
                # 연결된 시그널이 없는 경우 무시
                pass
        
        # 기존 트리 모델 초기화
        self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels(["Files/Folders"])
        
        # 타입과 이름으로 정렬
        items.sort(key=lambda x: (not x['is_dir'], x['path'].name.lower()))
        
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
                # 메타데이터 설정
                item_metadata = {
                    'is_dir': True,
                    'abs_path': str(self.current_folder),
                    'rel_path': str(root_rel_path)
                }
                root_item.setData(item_metadata, ITEM_DATA_ROLE)  # 메타데이터 추가
                item_dict[str(rel_path)] = root_item
                self.tree_model.appendRow(root_item)
                break
        
        if not root_item:
            # 루트 아이템이 없으면 생성
            root_item = QStandardItem(self.current_folder.name)
            root_item.setIcon(self.folder_icon)
            root_item.setCheckable(True)
            # 메타데이터 설정
            item_metadata = {
                'is_dir': True,
                'abs_path': str(self.current_folder),
                'rel_path': str(root_rel_path)
            }
            root_item.setData(item_metadata, ITEM_DATA_ROLE)  # 메타데이터 추가
            item_dict[str(root_rel_path)] = root_item
            self.tree_model.appendRow(root_item)
        
        logger.info(f"루트 아이템 생성 완료: {self.current_folder.name}")
        
        # 나머지 항목 처리 (루트 제외)
        for info in items:
            rel_path = info.get('rel_path')
            
            # 루트 아이템은 이미 처리함
            if rel_path == root_rel_path:
                continue
            
            path = info.get('path')
            is_dir = info.get('is_dir')
            
            # 부모 아이템 찾기 또는 필요시 생성
            parent_item = self._ensure_parent_item(rel_path, root_item, item_dict)
            
            # 현재 아이템 이름
            name = path.name
            
            # 이미 추가된 동일한 이름의 아이템이 있는지 확인
            already_exists = False
            for row in range(parent_item.rowCount()):
                child = parent_item.child(row)
                if child and child.text() == name:
                    already_exists = True
                    break
                    
            # 이미 존재하는 아이템이면 중복 추가하지 않음
            if already_exists:
                continue
                
            # 아이템 생성
            item = QStandardItem(name)
            item.setCheckable(True)
            
            # 아이콘 설정
            item.setIcon(self._get_item_icon(info))
            
            # 메타데이터 설정
            item_metadata = {
                'is_dir': is_dir,
                'abs_path': str(path),
                'rel_path': str(rel_path),
                'error': info.get('error', False),
                'is_symlink': info.get('is_symlink', False)
            }
            item.setData(item_metadata, ITEM_DATA_ROLE)
            
            # 아이템을 부모에 추가
            parent_item.appendRow(item)
            item_dict[str(rel_path)] = item
        
        # 시그널 다시 연결
        self.tree_model.itemChanged.connect(self.handle_item_change)
        if hasattr(self, '_processing_check_event'):
            self._processing_check_event = False
        
        # 모델 업데이트 시그널 발생
        self.model_updated_signal.emit(self.tree_model)
    
    def handle_item_change(self, item):
        """
        트리 아이템 체크 상태 변경 처리
        
        Args:
            item: 변경된 아이템
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
        
        # 파일인지 디렉토리인지 확인
        is_dir = item_path.is_dir() if item_path.exists() else False
        is_file = not is_dir
        path_str = str(item_path)
        
        try:
            # 일시적으로 모델 시그널 연결 해제
            self.tree_model.itemChanged.disconnect(self.handle_item_change)
            
            # 1. 현재 아이템 상태 업데이트 - 항상 즉시 처리
            if checked:
                self.checked_items.add(path_str)
            else:
                self.checked_items.discard(path_str)
            
            # 파일 항목인 경우와 디렉토리인 경우 처리 분리
            if is_file:
                # 파일인 경우 하위 처리 없이 즉시 체크 상태만 업데이트
                # 토큰 계산은 지연 실행
                
                # 체크 통계 빠르게 업데이트
                if checked:
                    self.checked_files += 1
                else:
                    self.checked_files = max(0, self.checked_files - 1)
                
                # UI 업데이트를 위한 시그널만 지연 발생
                QTimer.singleShot(0, lambda: self.selection_changed_signal.emit(
                    self.checked_files, 
                    self.checked_dirs,
                    self.checked_items
                ))
            else:
                # 디렉토리인 경우 자식 아이템에만 상태 전파
                # 현재 아이템은 이미 체크 상태가 변경되어 있으므로 자식 아이템에만 적용
                row_count = item.rowCount()
                for row in range(row_count):
                    child_item = item.child(row)
                    if child_item and child_item.isCheckable() and child_item.isEnabled():
                        self._set_item_checked_state(child_item, checked)
                
                # 3. 부모 폴더의 체크 상태 업데이트
                self._update_parent_checked_state(item)
                
                # 4. 체크 통계 업데이트
                self._update_check_stats()
                
                # 5. UI 응답성 향상을 위해 selection_changed_signal은 지연 발생
                QTimer.singleShot(0, lambda: self.selection_changed_signal.emit(
                    self.checked_files, 
                    self.checked_dirs,
                    self.checked_items
                ))
                
        finally:
            # 모델 시그널 다시 연결
            self.tree_model.itemChanged.connect(self.handle_item_change)
            self._processing_check_event = False
    
    def _set_item_checked_state(self, item, checked):
        """
        아이템과 모든 자식 아이템의 체크 상태를 설정
        
        Args:
            item: 설정할 아이템
            checked: 체크 상태
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
        
        Args:
            item: 자식 아이템
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
        아이템의 경로를 반환
        
        Args:
            item: 경로를 찾을 아이템
            
        Returns:
            Path 객체 또는 None
        """
        if not item or not self.current_folder:
            return None
        
        # 메타데이터에서 경로 정보 가져오기
        metadata = item.data(ITEM_DATA_ROLE)
        if isinstance(metadata, dict) and 'abs_path' in metadata:
            return Path(metadata['abs_path'])
        
        # 아이템 모델 인덱스 가져오기
        index = item.index()
        if not index.isValid():
            return None
        
        # 텍스트 기반 경로 구성 (기존 방식)
        path_components = []
        
        # 현재 아이템 이름
        text = item.text()
        if not text:
            return None
        
        path_components.append(text)
        
        # 부모 항목들 따라가기
        parent = item.parent()
        while parent:
            parent_text = parent.text()
            # 루트 아이템이면 멈춤 (이미 현재 폴더명이므로)
            if not parent.parent():  
                break
            path_components.append(parent_text)
            parent = parent.parent()
        
        # 역순으로 경로 구성 (자식→부모 순서로 모았으므로)
        path_components.reverse()
        
        # 상대 경로 구성
        rel_path = Path(*path_components)
        
        # 절대 경로로 변환
        abs_path = self.current_folder / rel_path
        
        return abs_path
    
    def _update_check_stats(self):
        """체크 상태 통계 업데이트 및 시그널 발생"""
        # 체크 상태 통계 계산
        self.checked_files = sum(1 for path in self.checked_items if Path(path).is_file())
        self.checked_dirs = sum(1 for path in self.checked_items if Path(path).is_dir())
        
        # 선택 변경 시그널 발생 (파일 수, 폴더 수, 체크된 아이템 Set 전체를 전달)
        self.selection_changed_signal.emit(self.checked_files, self.checked_dirs, self.checked_items)
    
    def clear_selection(self):
        """선택 항목 모두 해제"""
        if not self.checked_items:
            return
        
        # 모든 체크 항목 해제 로직
        self._processing_check_event = True
        try:
            # 시그널 일시 해제
            self.tree_model.itemChanged.disconnect(self.handle_item_change)
            
            # 루트 아이템부터 모든 체크된 항목을 해제
            root = self.tree_model.invisibleRootItem()
            
            # 모든 아이템 재귀적으로 순회하면서 체크 해제
            self._uncheck_item_recursive(root)
                
            # 상태 초기화
            self.checked_items.clear()
            self.checked_files = 0
            self.checked_dirs = 0
            
            # 선택 변경 시그널 발생
            self.selection_changed_signal.emit(self.checked_files, self.checked_dirs, self.checked_items)
            
        finally:
            # 시그널 다시 연결
            self.tree_model.itemChanged.connect(self.handle_item_change)
            self._processing_check_event = False
            
        logger.debug("모든 선택 항목 해제 완료")
    
    def _uncheck_item_recursive(self, item):
        """
        아이템과 모든 하위 아이템을 재귀적으로 체크 해제
        
        Args:
            item: 체크 해제할 최상위 아이템
        """
        if item.isCheckable():
            item.setCheckState(Qt.Unchecked)
            
        # 자식 항목 처리
        for row in range(item.rowCount()):
            child = item.child(row)
            if child:
                self._uncheck_item_recursive(child)
    
    def find_item_by_path(self, path: Path) -> Optional[QStandardItem]:
        """
        경로에 해당하는 트리 아이템 찾기
        
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
            
        # 루트 아이템 반환 (경로 부분이 없는 경우)
        if len(rel_path.parts) == 0:
            return parent_item
            
        # 경로의 각 부분에 대해 자식 아이템 찾기
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
    
    def toggle_hidden_files(self):
        """
        숨김 파일/폴더 표시 토글
        
        Returns:
            bool: 변경된 숨김 파일 표시 상태
        """
        self.show_hidden = not self.show_hidden
        if self.current_folder:
            self.load_folder(str(self.current_folder))
            
        return self.show_hidden
    
    def get_tree_model(self):
        """
        트리 모델 반환
        
        Returns:
            트리 모델
        """
        return self.tree_model
    
    def get_current_folder(self):
        """
        현재 폴더 반환
        
        Returns:
            현재 폴더 경로
        """
        return self.current_folder
    
    def get_checked_items(self):
        """
        체크된 항목 집합 반환
        
        Returns:
            체크된 항목 경로 집합
        """
        return self.checked_items
    
    def get_checked_files_count(self):
        """
        체크된 파일 수 반환
        
        Returns:
            체크된 파일 수
        """
        return self.checked_files
    
    def get_checked_dirs_count(self):
        """
        체크된 폴더 수 반환
        
        Returns:
            체크된 폴더 수
        """
        return self.checked_dirs
    
    def toggle_gitignore_filter(self):
        """
        .gitignore 필터링 설정 토글
        
        현재 설정을 반대로 변경하고, 필요시 현재 폴더를 다시 로드합니다.
        """
        self.apply_gitignore_rules = not self.apply_gitignore_rules
        
        # 로그
        logger.info(f".gitignore 필터 설정 변경: {self.apply_gitignore_rules}")
        
        # 현재 폴더가 있으면 다시 로드
        if self.current_folder:
            self.load_folder(str(self.current_folder))
            
        return self.apply_gitignore_rules

    def get_show_hidden(self):
        """
        숨김 파일 표시 상태 반환
        
        Returns:
            bool: 숨김 파일 표시 상태
        """
        return self.show_hidden
    
    def get_apply_gitignore_rules(self):
        """
        .gitignore 필터링 적용 상태 반환
        
        Returns:
            bool: .gitignore 필터링 적용 상태
        """
        return self.apply_gitignore_rules

    def _get_item_icon(self, item_info: Dict[str, Any]) -> QIcon:
        """
        파일 정보에 기반하여 적절한 아이콘 반환
        
        Args:
            item_info: 아이템 정보 딕셔너리
        
        Returns:
            QIcon: 항목에 적합한 아이콘
        """
        # 디렉토리인 경우
        if item_info.get('is_dir', False):
            return self.folder_icon
            
        # 에러가 있는 경우
        if item_info.get('error'):
            return self.error_icon
            
        # 심볼릭 링크인 경우
        if item_info.get('is_symlink', False):
            return self.symlink_icon
            
        # 파일인 경우 확장자에 따라 아이콘 결정
        path = item_info.get('path')
        if path:
            ext = path.suffix.lower()
            
            # 코드 파일
            if ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.c', '.cpp', '.h', '.java', '.cs', '.php', '.rb', '.go', '.rs']:
                return self.code_file_icon
                
            # 문서 파일
            elif ext in ['.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.html', '.css', '.scss', '.sass', '.doc', '.docx', '.pdf']:
                return self.doc_file_icon
                
            # 이미지 파일
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp']:
                return self.image_file_icon
        
        # 기본 파일 아이콘
        return self.file_icon
    
    def _ensure_parent_item(self, rel_path: Path, root_item: QStandardItem, item_dict: Dict[str, QStandardItem]) -> QStandardItem:
        """
        상대 경로의 부모 항목을 찾거나 생성
        
        Args:
            rel_path: 상대 경로
            root_item: 루트 아이템
            item_dict: 아이템 사전
            
        Returns:
            부모 아이템
        """
        # 루트 아이템의 자식인 경우
        if len(rel_path.parts) == 1:
            return root_item
            
        # 부모 경로 계산
        parent_path = rel_path.parent
        
        # 부모 아이템이 이미 생성되어 있는 경우
        if str(parent_path) in item_dict:
            return item_dict[str(parent_path)]
            
        # 가장 상위 부모부터 차례로 생성 (재귀적으로)
        grandparent_item = self._ensure_parent_item(parent_path, root_item, item_dict)
        
        # 현재 부모 이름 (parent_path의 마지막 부분)
        parent_name = parent_path.name if parent_path.name else parent_path
        
        # 이미 추가된 동일한 이름의 아이템이 있는지 확인
        for row in range(grandparent_item.rowCount()):
            child = grandparent_item.child(row)
            if child and child.text() == parent_name:
                item_dict[str(parent_path)] = child
                return child
        
        # 부모 아이템 생성
        parent_item = QStandardItem(parent_name)
        parent_item.setIcon(self.folder_icon)
        parent_item.setCheckable(True)
        
        # 메타데이터 설정
        parent_metadata = {
            'is_dir': True,
            'abs_path': str(self.current_folder / parent_path),
            'rel_path': str(parent_path)
        }
        parent_item.setData(parent_metadata, ITEM_DATA_ROLE)
        
        # 부모 아이템을 다시 상위 아이템에 추가
        grandparent_item.appendRow(parent_item)
        item_dict[str(parent_path)] = parent_item
        
        return parent_item 