#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
커스텀 위젯 모듈
애플리케이션에서 사용되는 재사용 가능한 커스텀 위젯 컴포넌트를 정의합니다.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import time

from PySide6.QtWidgets import (
    QTreeView, QStyledItemDelegate, QStyleOptionViewItem, QStyle, 
    QApplication, QProxyStyle
)
from PySide6.QtCore import Qt, Signal, QModelIndex, QEvent, QRect, QPoint, QTimer
from PySide6.QtGui import QPainter, QCursor, QStandardItemModel, QStandardItem

from src.gui.constants import ITEM_DATA_ROLE

logger = logging.getLogger(__name__)

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
        # 루트 폴더 확장/축소 타임스탬프 (중복 입력 방지용)
        self._last_root_toggle_time = 0
        # 디바운싱 시간 간격 (초 단위)
        self._debounce_interval = 0.8
        # 이벤트 처리 잠금 시간 (절대적인 잠금 시간)
        self._root_event_lock_until = 0
        # _setExpanded 메서드 호출 보호를 위한 잠금 시간
        self._setExpanded_lock_until = 0
        # 루트 항목 이벤트 완전 무시 모드
        self._hard_event_block = False
        
        # 시그널 연결: 트리 뷰의 expanded/collapsed 시그널을 내부 슬롯에 연결
        self.expanded.connect(self._handle_expanded)
        self.collapsed.connect(self._handle_collapsed)
        
        # 하드 블로킹 해제 타이머
        self._hard_block_timer = QTimer(self)
        self._hard_block_timer.setSingleShot(True)
        self._hard_block_timer.timeout.connect(self._reset_hard_block)
        
        # 체크 상태 복원을 위한 임시 저장소
        self._check_states = {}
        
        # FileTreeController 참조 (나중에 설정됨)
        self._controller = None
    
    def set_controller(self, controller):
        """
        FileTreeController 참조 설정
        
        Args:
            controller: FileTreeController 인스턴스
        """
        self._controller = controller
    
    def _save_check_states(self, index):
        """
        지정된 인덱스의 아이템과 모든 하위 아이템의 체크 상태를 저장
        
        Args:
            index: 저장할 아이템의 모델 인덱스
        """
        model = self.model()
        if not model:
            return
            
        item = model.itemFromIndex(index)
        if not item:
            return
            
        # 현재 아이템의 체크 상태 저장
        if item.isCheckable():
            metadata = item.data(ITEM_DATA_ROLE)
            if isinstance(metadata, dict) and 'abs_path' in metadata:
                self._check_states[metadata['abs_path']] = item.checkState()
        
        # 모든 자식 아이템의 체크 상태 저장
        for row in range(item.rowCount()):
            child_index = model.index(row, 0, index)
            self._save_check_states(child_index)
    
    def _restore_check_states(self, index):
        """
        지정된 인덱스의 아이템과 모든 하위 아이템의 체크 상태를 복원
        
        Args:
            index: 복원할 아이템의 모델 인덱스
        """
        model = self.model()
        if not model:
            return
            
        item = model.itemFromIndex(index)
        if not item:
            return
            
        # 현재 아이템의 체크 상태 복원
        if item.isCheckable():
            metadata = item.data(ITEM_DATA_ROLE)
            if isinstance(metadata, dict) and 'abs_path' in metadata:
                saved_state = self._check_states.get(metadata['abs_path'])
                if saved_state is not None:
                    item.setCheckState(saved_state)
        
        # 모든 자식 아이템의 체크 상태 복원
        for row in range(item.rowCount()):
            child_index = model.index(row, 0, index)
            self._restore_check_states(child_index)

    def _reset_hard_block(self):
        """하드 블로킹 모드 해제"""
        logger.debug("하드 블로킹 모드 해제")
        self._hard_event_block = False

    def _perform_folder_toggle(self, index, is_root=False):
        """
        하위 폴더 확장/축소 작업을 수행하는 메서드
        (루트 폴더는 mouseReleaseEvent에서 직접 처리)
        
        Args:
            index: 처리할 아이템의 모델 인덱스
            is_root: 루트 폴더 여부 (루트 폴더는 무시됨)
        """
        # 루트 폴더는 더 이상 이 메서드로 처리하지 않음
        if is_root:
            logger.debug("루트 폴더는 _perform_folder_toggle을 통해 처리되지 않음")
            return
            
        # 현재 확장 상태 확인
        is_expanded = self.isExpanded(index)
        
        # 하위 폴더 - 단순 처리
        logger.debug("하위 폴더 %s 수행", "확장" if not is_expanded else "축소")
        if is_expanded:
            self.collapse(index)
        else:
            self.expand(index)

    def mousePressEvent(self, event):
        """마우스 누름 이벤트 처리"""
        # 클릭 위치 저장
        self._press_pos = event.pos()
        index = self.indexAt(event.pos())
        
        # 현재 시간 확인
        current_time = time.time()
        
        # 하드 블로킹 확인 - 루트 폴더에 대한 모든 이벤트 무시
        if self._hard_event_block and index.isValid() and not index.parent().isValid():
            logger.debug("하드 블로킹 모드: 루트 폴더 마우스 이벤트 무시")
            event.accept()
            return
        
        # 이벤트 잠금 상태 확인 - 잠금 기간 내라면 모든 클릭 무시
        if current_time < self._root_event_lock_until:
            logger.debug("이벤트 잠금 기간: 클릭 무시 (남은 시간: %f초)", 
                        self._root_event_lock_until - current_time)
            event.accept()
            return
        
        # 루트 항목이고 브랜치 인디케이터 영역인 경우 특별 처리
        if index.isValid() and not index.parent().isValid():
            is_branch_area = self._is_branch_indicator_area(index, event.pos())
            if is_branch_area:
                # 클릭 위치 및 인덱스 정보만 저장 (단순화)
                logger.debug("루트 폴더 브랜치 영역 클릭: 위치 정보 저장")
                # 이벤트 소비하여 Qt의 기본 확장/축소 동작 차단
                event.accept()
                # 부모 클래스의 mousePressEvent를 호출하지 않고 종료
                return
        
        if index.isValid():
            # 체크박스 영역 확인
            is_checkbox_click = self._is_checkbox_area(index, event.pos())
            
            # 체크박스 영역이면 플래그 설정하고 이벤트 소비
            if is_checkbox_click:
                self._checkbox_click_in_progress = True
                event.accept()
                return
        
        # 체크박스 영역이 아닌 경우 기본 마우스 이벤트 처리
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """마우스 놓음 이벤트 처리"""
        # 클릭한 인덱스 가져오기
        index = self.indexAt(event.pos())
        
        # 현재 시간 확인
        current_time = time.time()
        
        # 이벤트 잠금 상태 확인 - 잠금 기간 내라면 이벤트 무시
        if current_time < self._root_event_lock_until:
            logger.debug("이벤트 잠금 기간: 마우스 릴리즈 무시 (남은 시간: %f초)", 
                          self._root_event_lock_until - current_time)
            event.accept()
            return
        
        try:
            # 루트 항목 클릭 처리
            if (index.isValid() and not index.parent().isValid() and self._press_pos):
                # 클릭 시작과 릴리즈가 같은 인덱스에 있는지 확인
                press_index = self.indexAt(self._press_pos)
                if press_index == index:
                    # 브랜치 인디케이터 영역인지 확인
                    is_branch_area = self._is_branch_indicator_area(index, event.pos())
                    if is_branch_area:
                        # 디바운싱 체크 - 짧은 시간 내 중복 호출 방지
                        if current_time - self._last_root_toggle_time < self._debounce_interval:
                            logger.debug("루트 폴더 토글 무시: 디바운싱 (%f초)", 
                                        current_time - self._last_root_toggle_time)
                            event.accept()
                            return
                        
                        # 마지막 토글 시간 갱신
                        self._last_root_toggle_time = current_time
                        
                        # _setExpanded 메서드 호출 시 보호할 쿨다운 설정 (200ms)
                        self._setExpanded_lock_until = current_time + 0.2
                        
                        # 하드 블로킹 모드 활성화 - 후속 이벤트 차단
                        self._hard_event_block = True
                        self._hard_block_timer.start(int(self._debounce_interval * 1000))
                        
                        logger.debug("루트 폴더 %s 명시적 제어", "확장" if not self.isExpanded(index) else "축소")
                        
                        # 확장/축소 상태 명시적 변경
                        if self.isExpanded(index):
                            self.collapse(index)
                        else:
                            self.expand(index)
                        
                        # 이벤트 소비
                        event.accept()
                        return

            # 유효하지 않은 인덱스인 경우 기본 처리 후 종료
            if not index.isValid():
                super().mouseReleaseEvent(event)
                return
            
            # 체크박스 클릭 진행 상황 확인 (가장 높은 우선순위)
            if self._checkbox_click_in_progress:
                # 현재 마우스 위치가 체크박스 영역인지 확인
                is_current_pos_checkbox = self._is_checkbox_area(index, event.pos())
                
                if is_current_pos_checkbox:
                    # 체크박스 상태 토글
                    model = self.model()
                    if model:
                        current_state = model.data(index, Qt.CheckStateRole)
                        new_state = Qt.Unchecked if current_state == Qt.Checked else Qt.Checked
                        model.setData(index, new_state, Qt.CheckStateRole)
                    
                    # 체크박스 클릭 시그널 발생
                    self.checkbox_clicked.emit(index)
                    event.accept()
                    return
                else:
                    # 체크박스 영역 밖에서 마우스를 뗀 경우 아무 동작도 하지 않음
                    event.accept()
                    return
            
            # 체크박스 클릭이 아닌 경우 파일/디렉토리 처리
            model = self.model()
            if model:
                item = model.itemFromIndex(index)
                metadata = item.data(ITEM_DATA_ROLE) if item else None
                
                # 파일인 경우 - item_clicked 시그널 발생
                if item and (not isinstance(metadata, dict) or not metadata.get('is_dir', False)):
                    # press_pos와 현재 위치가 같은 인덱스에 있고, 브랜치 인디케이터 영역이 아닌 경우
                    press_index = self.indexAt(self._press_pos) if self._press_pos else None
                    is_branch_area = self._is_branch_indicator_area(index, event.pos())
                    
                    if press_index == index and not is_branch_area:
                        self.item_clicked.emit(index)
                        event.accept()
                        return
                
                # 디렉토리인 경우 - 확장/축소 처리
                elif item and isinstance(metadata, dict) and metadata.get('is_dir', False):
                    is_branch_area = self._is_branch_indicator_area(index, event.pos())
                    press_index = self.indexAt(self._press_pos) if self._press_pos else None
                    
                    # 루트 폴더인지 확인 (부모가 없는 경우)
                    is_root = not index.parent().isValid()
                    
                    # 루트 폴더와 하위 폴더 모두 통합 메서드로 처리
                    if is_branch_area or (not is_branch_area and press_index == index and 
                                         not self._is_checkbox_area(index, event.pos())):
                        # 하위 폴더만 통합 메서드로 폴더 토글 처리
                        if not is_root:
                            self._perform_folder_toggle(index, is_root=False)
                            event.accept()
                            return
                        # 루트 폴더는 이미 상단에서 처리됨
            
            # 어떤 조건에도 해당하지 않으면 기본 마우스 릴리스 이벤트 처리
            super().mouseReleaseEvent(event)
            
        finally:
            # 항상 플래그 및 클릭 위치 초기화
            self._checkbox_click_in_progress = False
            self._press_pos = None

    def _handle_expanded(self, index):
        """
        트리 항목 확장 시 호출되는 핸들러
        루트 항목 확장 시 추가 제어 수행
        """
        # 하드 블로킹 모드 확인 (루트 항목인 경우)
        if index.isValid() and not index.parent().isValid() and self._hard_event_block:
            logger.debug("루트 항목 확장 이벤트 - 하드 블로킹으로 인한 무시")
            return
            
        # 컨트롤러가 설정되어 있으면 컨트롤러의 메서드 호출
        if self._controller and hasattr(self._controller, '_handle_expanded'):
            self._controller._handle_expanded(index)
        else:
            # 기존 방식으로 체크 상태 복원
            QTimer.singleShot(0, lambda: self._restore_check_states(index))
    
    def _handle_collapsed(self, index):
        """
        트리 항목 축소 시 호출되는 핸들러
        루트 항목 축소 시 추가 제어 수행
        """
        # 하드 블로킹 모드 확인 (루트 항목인 경우)
        if index.isValid() and not index.parent().isValid() and self._hard_event_block:
            logger.debug("루트 항목 축소 이벤트 - 하드 블로킹으로 인한 무시")
            return
            
        # 컨트롤러가 설정되어 있으면 컨트롤러의 메서드 호출
        if self._controller and hasattr(self._controller, '_handle_collapsed'):
            self._controller._handle_collapsed(index)
        else:
            # 기존 방식으로 체크 상태 저장
            self._save_check_states(index)

    def _setExpanded(self, index, expanded):
        """
        내부 확장/축소 상태 변경 메서드 오버라이드
        루트 항목의 경우 중복 처리를 방지
        """
        # 루트 항목 확인
        if not index.parent().isValid():
            # 현재 시간 확인
            current_time = time.time()
            
            # _setExpanded 잠금 시간 내에 있는지 확인
            if current_time < self._setExpanded_lock_until:
                logger.debug("루트 항목 _setExpanded - 쿨다운 기간 내 호출 무시 (%f초 남음)",
                            self._setExpanded_lock_until - current_time)
                return
                
            # 하드 블로킹 모드 확인
            if self._hard_event_block:
                logger.debug("루트 항목 _setExpanded - 하드 블로킹으로 인한 무시")
                return
            
            # 이벤트 잠금 시간 내에 있는지 확인
            if current_time < self._root_event_lock_until:
                logger.debug("루트 항목 _setExpanded - 잠금 기간 내 요청 차단 (%f초 남음)",
                            self._root_event_lock_until - current_time)
                return
        
        # 루트 항목이 아니거나, 명시적 처리가 필요한 경우 기본 처리 호출
        super()._setExpanded(index, expanded)

    def _is_checkbox_area(self, index, pos):
        """
        주어진 위치(pos)가 해당 아이템(index)의 체크박스 영역 내에 있는지 확인하는 메소드
        
        Args:
            index: 트리 아이템의 모델 인덱스
            pos: 확인할 마우스 커서 위치(QPoint)
            
        Returns:
            boolean: 마우스 위치가 체크박스 영역 내에 있으면 True, 그렇지 않으면 False
        """
        # 모델이 없으면 체크박스도 없음
        model = self.model()
        if not model:
            return False
            
        # 해당 인덱스에 체크 상태가 정의되어 있는지 확인
        # (체크 상태가 없으면 체크박스가 표시되지 않음)
        if model.data(index, Qt.CheckStateRole) is None:
            return False
            
        # 현재 아이템의 시각적 영역 가져오기
        item_visual_rect = self.visualRect(index)
        
        # 아이템 정보 확인 (폴더 여부)
        is_folder = False
        item = model.itemFromIndex(index)
        if item:
            metadata = item.data(ITEM_DATA_ROLE)
            is_folder = isinstance(metadata, dict) and metadata.get('is_dir', False)
            
        # QStyleOptionViewItem 설정 - Qt 스타일링 시스템에서 사용
        style_option = QStyleOptionViewItem()
        style_option.initFrom(self)  # 현재 위젯에서 스타일 옵션 초기화
        style_option.rect = item_visual_rect  # 아이템의 시각적 영역 설정
        
        # 아이템의 활성화 상태 및 포커스 상태 설정
        if self.isEnabled():
            style_option.state |= QStyle.State_Enabled  # 위젯이 활성화 상태인 경우
        if self.currentIndex() == index:
            style_option.state |= QStyle.State_HasFocus  # 현재 아이템에 포커스가 있는 경우
        
        # 체크박스의 상태 설정 (체크됨, 부분 체크, 체크 안됨)
        current_check_state = model.data(index, Qt.CheckStateRole)
        if current_check_state == Qt.Checked:
            style_option.state |= QStyle.State_On  # 체크됨
        elif current_check_state == Qt.PartiallyChecked:
            style_option.state |= QStyle.State_NoChange  # 부분 체크
        else:
            style_option.state |= QStyle.State_Off  # 체크 안됨
        
        # 아이템의 특성 설정 (체크박스, 아이콘, 텍스트 등)
        # 체크박스 표시 특성 설정
        style_option.features |= QStyleOptionViewItem.HasCheckIndicator
        
        # 아이콘 표시 특성 설정 (있는 경우만)
        if model.data(index, Qt.DecorationRole):
            style_option.features |= QStyleOptionViewItem.HasDecoration
        
        # 텍스트 표시 특성 설정 (있는 경우만)
        if model.data(index, Qt.DisplayRole):
            style_option.features |= QStyleOptionViewItem.HasDisplay
        
        # 현재 스타일 엔진 가져오기
        current_style = self.style()
        
        # 체크박스 영역 계산 - Qt 스타일 시스템을 통해 계산됨
        checkbox_rect = current_style.subElementRect(QStyle.SE_ItemViewItemCheckIndicator, style_option, self)
        
        # Qt 스타일 시스템이 유효한 체크박스 영역을 반환하지 않은 경우 
        # (일부 스타일이나 플랫폼에서 발생할 수 있음)
        if checkbox_rect.width() <= 0 or checkbox_rect.height() <= 0:
            # 대체 계산 로직: 기본 체크박스 크기와 위치를 수동으로 계산
            
            # 체크박스 크기 가져오기 (픽셀 지표를 통해)
            checkbox_width = current_style.pixelMetric(QStyle.PM_IndicatorWidth, style_option, self)
            checkbox_height = current_style.pixelMetric(QStyle.PM_IndicatorHeight, style_option, self)
            
            # 왼쪽 여백 가져오기
            left_margin = current_style.pixelMetric(QStyle.PM_LayoutLeftMargin)
            
            # 체크박스 X 위치: 아이템 시작 위치 + 왼쪽 여백
            checkbox_x = item_visual_rect.x() + left_margin
            
            # 체크박스 Y 위치: 아이템 중앙에 수직 정렬
            checkbox_y = item_visual_rect.y() + (item_visual_rect.height() - checkbox_height) // 2
            
            # 체크박스 영역 생성
            checkbox_rect = QRect(checkbox_x, checkbox_y, checkbox_width, checkbox_height)
        
        # 사용자 클릭의 정확도를 높이기 위해 체크박스 영역을 확장
        # 폴더 항목의 경우 더 넓은 영역을 제공하여 체크박스 접근성 향상
        horizontal_padding = 5  # 기본 수평 패딩
        vertical_padding = 5    # 기본 수직 패딩
        
        if is_folder:
            # 폴더 항목은 체크박스 영역을 좀 더 넓게 설정
            horizontal_padding = 8
            vertical_padding = 8
            
        # 체크박스 영역 확장 적용
        checkbox_rect.adjust(
            -horizontal_padding,    # 좌측 확장
            -vertical_padding,      # 상단 확장
            horizontal_padding,     # 우측 확장
            vertical_padding        # 하단 확장
        )
        
        # 디버깅 로그 추가
        logger.debug("체크박스 영역 계산: rect=%s, 마우스 위치=%s, 포함=%s, 폴더=%s", 
                    checkbox_rect, pos, checkbox_rect.contains(pos), is_folder)
        
        # 마우스 위치가 체크박스 영역 내에 있는지 확인하여 결과 반환
        return checkbox_rect.contains(pos)
    
    def _is_branch_indicator_area(self, index, pos):
        """
        주어진 위치(pos)가 해당 아이템(index)의 브랜치 인디케이터(폴더 확장/축소 아이콘) 영역 내에 있는지 확인하는 메소드
        
        이 메소드는 트리 뷰에서 폴더 아이템 앞에 표시되는 [+]/[-] 확장/축소 아이콘 영역을 식별합니다.
        
        Args:
            index: 트리 아이템의 모델 인덱스
            pos: 확인할 마우스 커서 위치(QPoint)
            
        Returns:
            boolean: 마우스 위치가 브랜치 인디케이터 영역 내에 있으면 True, 그렇지 않으면 False
        """
        # 현재 아이템의 시각적 영역 가져오기
        item_visual_rect = self.visualRect(index)
        
        # 들여쓰기 크기 가져오기 (각 트리 레벨의 들여쓰기 픽셀 단위)
        indentation_width = self.indentation()
        
        # 현재 아이템의 트리 깊이(레벨) 계산
        # 루트 레벨은 0, 그 아래 각 레벨은 1씩 증가
        tree_depth = 0
        parent_index = index.parent()
        while parent_index.isValid():
            tree_depth += 1
            parent_index = parent_index.parent()
        
        # 브랜치 인디케이터 영역 계산
        # 브랜치 인디케이터는 아이템 텍스트 왼쪽의 들여쓰기 영역에 위치
        # 전체 들여쓰기 영역의 너비는 (트리 깊이 * 들여쓰기 크기)
        branch_area_width = tree_depth * indentation_width
        
        # 브랜치 인디케이터 영역 생성
        # X 좌표는 아이템의 시각적 시작점에서 들여쓰기 영역만큼 왼쪽으로 이동
        # 높이는 아이템 전체 높이와 동일
        branch_indicator_rect = QRect(
            item_visual_rect.x() - branch_area_width,  # 시작 X 좌표
            item_visual_rect.y(),                      # 시작 Y 좌표
            branch_area_width,                         # 너비
            item_visual_rect.height()                  # 높이
        )
        
        # 마우스 위치가 브랜치 인디케이터 영역 내에 있는지 확인하여 결과 반환
        return branch_indicator_rect.contains(pos)

    def mouseDoubleClickEvent(self, event):
        """더블 클릭 이벤트 처리"""
        # 디버깅을 위한 로그
        logger.debug("더블 클릭 이벤트 발생")
                    
        # 더블 클릭한 아이템의 인덱스 가져오기
        index = self.indexAt(event.pos())
        
        # 현재 시간 확인
        current_time = time.time()
        
        # 이벤트 잠금 상태 확인 - 잠금 기간 내라면 이벤트 무시
        if current_time < self._root_event_lock_until:
            logger.debug("이벤트 잠금 기간: 더블 클릭 무시 (남은 시간: %f초)", 
                       self._root_event_lock_until - current_time)
            event.accept()
            return
        
        if index.isValid():
            # 체크박스나 브랜치 인디케이터 영역인지 확인
            is_checkbox_area = self._is_checkbox_area(index, event.pos())
            is_branch_area = self._is_branch_indicator_area(index, event.pos())
            
            # 디버깅 로그 추가
            logger.debug("더블 클릭 위치 확인: 체크박스 영역=%s, 브랜치 인디케이터 영역=%s",
                         is_checkbox_area, is_branch_area)
            
            # 체크박스나 브랜치 인디케이터 영역이 아닌 경우에만 폴더 확장/축소 처리
            if not is_checkbox_area and not is_branch_area:
                # 모델에서 해당 아이템이 디렉토리인지 확인
                model = self.model()
                if model:
                    item = model.itemFromIndex(index)
                    metadata = item.data(ITEM_DATA_ROLE) if item else None
                    
                    # 디렉토리인 경우 - 통합 메서드로 처리
                    if item and isinstance(metadata, dict) and metadata.get('is_dir', False):
                        # 루트 폴더인지 확인
                        is_root = not index.parent().isValid()
                        # 통합 메서드로 폴더 토글 처리
                        self._perform_folder_toggle(index, is_root=is_root)
                            
                    # 파일 항목인 경우 - item_clicked 시그널 발생
                    elif item and not metadata.get('is_dir', False):
                        logger.debug("더블 클릭으로 파일 항목 클릭 발생: %s", item.text() if item else "알 수 없음")
                        self.item_clicked.emit(index)
            else:
                # 체크박스 영역 더블 클릭 시 체크박스 상태 토글 없이 이벤트만 소비
                if is_checkbox_area:
                    logger.debug("체크박스 영역 더블 클릭: 폴더 확장/축소 동작 없음")
                # 브랜치 인디케이터 영역 더블 클릭 시 이벤트만 소비
                elif is_branch_area:
                    logger.debug("브랜치 인디케이터 영역 더블 클릭: 폴더 확장/축소 동작 없음")
        
        # 이벤트 소비 (기본 처리 방지)
        event.accept()
        
        # 상태 플래그 명확히 초기화
        self._checkbox_click_in_progress = False
        self._press_pos = None
    
    # QTreeView의 기본 클릭 처리 방지
    def keyPressEvent(self, event):
        """키 입력 이벤트 처리"""
        # 확장/축소와 관련된 키는 직접 처리 
        # (Enter, Return, Right, Left 등의 키)
        key = event.key()
        current_index = self.currentIndex()
        
        # 현재 시간 확인
        current_time = time.time()
        
        # 이벤트 잠금 상태 확인 - 잠금 기간 내라면 이벤트 무시 (루트 항목인 경우)
        if (current_time < self._root_event_lock_until and 
            current_index.isValid() and 
            not current_index.parent().isValid()):
            logger.debug("이벤트 잠금 기간: 키 입력 무시 (남은 시간: %f초)", 
                        self._root_event_lock_until - current_time)
            event.accept()
            return
        
        if current_index.isValid():
            # 모델에서 현재 항목이 디렉토리인지 확인
            model = self.model()
            if model:
                item = model.itemFromIndex(current_index)
                metadata = item.data(ITEM_DATA_ROLE) if item else None
                is_directory = item and isinstance(metadata, dict) and metadata.get('is_dir', False)
                
                # 루트 폴더인지 확인
                is_root = not current_index.parent().isValid()
                
                if key in (Qt.Key_Right, Qt.Key_Enter, Qt.Key_Return):
                    # 폴더인 경우에만 확장 처리
                    if is_directory:
                        if not self.isExpanded(current_index):
                            # 통합 메서드로 폴더 확장 처리
                            self._perform_folder_toggle(current_index, is_root=is_root)
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
                            # 통합 메서드로 폴더 축소 처리
                            self._perform_folder_toggle(current_index, is_root=is_root)
                            event.accept()
                            return
        
        # 나머지 키 이벤트는 기본 처리
        super().keyPressEvent(event)

    def event(self, event):
        """기본 이벤트 처리 메서드 오버라이드"""
        # 하드 블로킹 상태에서는 루트 항목 관련 이벤트 무시
        if self._hard_event_block:
            if event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease, 
                               QEvent.MouseButtonDblClick, QEvent.MouseMove):
                # 마우스 이벤트일 경우만 추가 검사
                pos = event.pos()
                index = self.indexAt(pos)
                if index.isValid() and not index.parent().isValid():
                    # 루트 항목에 대한 이벤트면 무시
                    is_branch_area = self._is_branch_indicator_area(index, pos)
                    if is_branch_area:
                        logger.debug("하드 블로킹: 루트 항목 기본 이벤트 무시: %s", event.type())
                        event.accept()
                        return True
        
        # 기본 이벤트 처리
        return super().event(event) 