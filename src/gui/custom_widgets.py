#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
커스텀 위젯 모듈
애플리케이션에서 사용되는 재사용 가능한 커스텀 위젯 컴포넌트를 정의합니다.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtWidgets import (
    QTreeView, QStyledItemDelegate, QStyleOptionViewItem, QStyle, 
    QApplication, QProxyStyle
)
from PySide6.QtCore import Qt, Signal, QModelIndex, QEvent, QRect, QPoint
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
        # 클릭한 인덱스 가져오기
        index = self.indexAt(event.pos())
        
        # 유효하지 않은 인덱스인 경우 기본 처리 후 종료
        if not index.isValid():
            super().mouseReleaseEvent(event)
            return
        
        # 체크박스 영역 클릭이 아닌 경우만 처리
        if not self._is_checkbox_area(index, event.pos()):
            model = self.model()
            if model:
                item = model.itemFromIndex(index)
                metadata = item.data(ITEM_DATA_ROLE) if item else None
                
                # 파일인 경우 즉시 처리하고 이벤트 소비
                if item and (not isinstance(metadata, dict) or not metadata.get('is_dir', False)):
                    self.item_clicked.emit(index)
                    event.accept()  # 이벤트 소비하여 중복 처리 방지
                    return  # 여기서 즉시 반환하여 추가 처리 방지
                
                # 디렉토리인 경우 확장/축소 처리
                elif item and isinstance(metadata, dict) and metadata.get('is_dir', False):
                    if self._is_branch_indicator_area(index, event.pos()) or (self._press_pos is not None and self.indexAt(self._press_pos) == index):
                        # 폴더 확장/축소 수동 처리
                        if self.isExpanded(index):
                            self.collapse(index)
                        else:
                            self.expand(index)
                        event.accept()
                        self._press_pos = None
                        return
        
        # 체크박스 클릭 처리
        if self._checkbox_click_in_progress and self._is_checkbox_area(index, event.pos()):
            # 체크박스 클릭 완료 - 기본 처리 호출 (체크박스 상태 변경)
            super().mouseReleaseEvent(event)
            
            # 체크박스 클릭 시그널 발생
            self.checkbox_clicked.emit(index)
            
            # 체크박스 클릭 플래그 초기화
            self._checkbox_click_in_progress = False
            
            # 이벤트 소비
            event.accept()
            return
        
        # 기본 마우스 릴리스 이벤트 처리
        super().mouseReleaseEvent(event)
        
        # 클릭 위치 초기화
        self._press_pos = None
    
    def mouseDoubleClickEvent(self, event):
        """더블 클릭 이벤트 처리"""
        # 더블 클릭한 아이템의 인덱스 가져오기
        index = self.indexAt(event.pos())
        
        if index.isValid():
            # 모델에서 해당 아이템이 디렉토리인지 확인
            model = self.model()
            if model:
                item = model.itemFromIndex(index)
                metadata = item.data(ITEM_DATA_ROLE) if item else None
                if item and isinstance(metadata, dict) and metadata.get('is_dir', False):  # 디렉토리인 경우
                    # 폴더 확장/축소 수동 처리
                    if self.isExpanded(index):
                        self.collapse(index)
                    else:
                        self.expand(index)
        
        # 이벤트 소비 (기본 처리 방지)
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
                metadata = item.data(ITEM_DATA_ROLE) if item else None
                is_directory = item and isinstance(metadata, dict) and metadata.get('is_dir', False)
                
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
        if not model.data(index, Qt.CheckStateRole):
            return False
            
        # 현재 아이템의 시각적 영역 가져오기
        item_visual_rect = self.visualRect(index)
        
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
            
            # 사용자 클릭의 정확도를 높이기 위해 체크박스 영역을 약간 확장
            # (작은 체크박스를 클릭하기 어려울 수 있으므로)
            checkbox_rect.adjust(-2, -2, 2, 2)  # 좌, 상, 우, 하 방향으로 각각 2픽셀 확장
        
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