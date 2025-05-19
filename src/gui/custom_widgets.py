#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
커스텀 위젯 모듈
애플리케이션에서 사용되는 재사용 가능한 커스텀 위젯 컴포넌트를 정의합니다.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QTreeView, QStyledItemDelegate, QStyleOptionViewItem, QStyle, 
    QApplication, QProxyStyle
)
from PySide6.QtCore import Qt, Signal, QModelIndex, QEvent, QRect
from PySide6.QtGui import QPainter, QCursor

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
                    if item and item.data(Qt.UserRole):  # 디렉토리인 경우
                        # 폴더 확장/축소 수동 처리
                        if self.isExpanded(index):
                            self.collapse(index)
                        else:
                            self.expand(index)
                        # 이벤트 소비
                        event.accept()
                    elif not (item and item.data(Qt.UserRole)):  # 파일인 경우만
                        # 일반 아이템 영역 클릭 시그널 발생 (파일만)
                        self.item_clicked.emit(index)
                        
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
                if item and item.data(Qt.UserRole):  # 디렉토리인 경우
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