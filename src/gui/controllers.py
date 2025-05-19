#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
컨트롤러 모듈
애플리케이션의 로직을 UI와 분리하여 처리하는 컨트롤러 클래스를 정의합니다.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Union, Tuple

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon

# 코어 모듈 임포트
from src.core.file_scanner import scan_directory, is_binary_file
from src.core.filter import GitignoreFilter
from src.core.sort_utils import sort_items

logger = logging.getLogger(__name__)


class FileTreeController(QObject):
    """
    파일 트리 컨트롤러
    파일 시스템 스캔, 트리 모델 관리, 아이템 선택 및 상태 변경 로직을 처리합니다.
    """
    
    # 시그널 정의
    folder_loaded_signal = Signal(list)  # 폴더 로드 완료 시 발생 (items 목록 전달)
    selection_changed_signal = Signal(int, int, set)  # 선택 변경 시 발생 (파일 수, 폴더 수, 체크된 항목 집합)
    model_updated_signal = Signal(QStandardItemModel)  # 모델 업데이트 시 발생 (업데이트된 모델 전달)
    
    def __init__(self, folder_icon=None, folder_open_icon=None, file_icon=None, code_file_icon=None, doc_file_icon=None):
        """
        FileTreeController 초기화
        
        Args:
            folder_icon: 폴더 아이콘
            folder_open_icon: 열린 폴더 아이콘
            file_icon: 일반 파일 아이콘
            code_file_icon: 코드 파일 아이콘
            doc_file_icon: 문서 파일 아이콘
        """
        super().__init__()
        
        # 아이콘 저장
        self.folder_icon = folder_icon
        self.folder_open_icon = folder_open_icon
        self.file_icon = file_icon
        self.code_file_icon = code_file_icon
        self.doc_file_icon = doc_file_icon
        
        # 트리 모델 초기화
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Files/Folders"])
        
        # 파일/폴더 관련 상태 변수
        self.current_folder = None  # 현재 폴더
        self.gitignore_filter = None  # .gitignore 필터
        self.show_hidden = False  # 숨김 파일 표시 여부
        
        # 체크 상태 추적
        self.checked_items = set()  # 체크된 항목 경로 집합
        self.checked_files = 0  # 체크된 파일 수
        self.checked_dirs = 0  # 체크된 폴더 수
        
        # 시그널 연결 플래그
        self._processing_check_event = False
        
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
            
            # .gitignore 필터 초기화
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
        
        logger.info(f"루트 아이템 생성 완료: {self.current_folder.name}")
        
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
            item.setCheckable(True)
            
            # 아이콘 설정
            if is_dir:
                item.setIcon(self.folder_icon)
                item.setData(True, Qt.UserRole)  # 디렉토리 플래그
            else:
                # 파일 확장자에 따라 아이콘 결정
                ext = path.suffix.lower()
                if ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.c', '.cpp', '.h', '.java', '.cs', '.php', '.rb', '.go', '.rs']:
                    item.setIcon(self.code_file_icon)
                elif ext in ['.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.html', '.css', '.scss', '.sass', '.doc', '.docx', '.pdf']:
                    item.setIcon(self.doc_file_icon)
                else:
                    item.setIcon(self.file_icon)
                item.setData(False, Qt.UserRole)  # 디렉토리가 아님을 표시
            
            # 아이템을 부모에 추가
            parent_item.appendRow(item)
            item_dict[rel_path] = item
        
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
        
        try:
            # 일시적으로 모델 시그널 연결 해제
            self.tree_model.itemChanged.disconnect(self.handle_item_change)
            
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
        
        # 선택 변경 시그널 발생
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
        """숨김 파일/폴더 표시 토글"""
        self.show_hidden = not self.show_hidden
        if self.current_folder:
            self.load_folder(str(self.current_folder))
    
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