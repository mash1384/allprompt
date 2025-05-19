# allprompt GUI 모듈화 최종 개선 및 책임 명확화

**개선 목표:** `MainWindow`의 역할을 순수 UI 프레임 및 중재자로 더욱 명확히 하고, 각 컨트롤러와 패널이 자신의 책임을 완전히 갖도록 하여 코드의 응집도를 높이고 결합도를 낮춥니다. 이를 통해 전체적인 코드 품질, 가독성, 유지보수성 및 테스트 용이성을 극대화합니다.

**일반 지침:**

*   모든 변경 사항은 기존 기능의 완벽한 유지 및 정상 동작을 보장해야 합니다.
*   각 클래스는 단일 책임 원칙(SRP)을 최대한 따르도록 합니다.
*   상태 정보는 해당 상태를 직접 관리하고 사용하는 컨트롤러 또는 컴포넌트가 유일하게 소유합니다(Single Source of Truth).
*   컴포넌트 간의 직접적인 내부 상태 접근을 최소화하고, 메소드 호출 및 시그널-슬롯 메커니즘을 통한 통신을 지향합니다.

---

**세부 지시사항:**

**I. `FileTreeController` 책임 완전 이전 및 강화 (`src/gui/controllers.py` 또는 `file_tree_controller.py` 및 `src/gui/main_window.py` 수정)**

1.  **`MainWindow`에서 `FileTreeController`로 상태 변수 완전 이전:**
    *   `MainWindow.__init__`에서 다음 상태 변수 초기화를 **제거**하고, 이들의 소유 및 관리를 `FileTreeController`로 **완전히 이전**하십시오:
        *   `checked_items`, `checked_files`, `checked_dirs`, `current_folder`, `gitignore_filter`, `show_hidden`.
    *   `FileTreeController`는 이 상태들을 내부적으로 관리하며, 필요시 getter 메소드나 시그널을 통해 외부(주로 `MainWindow`)에 제공합니다.

2.  **`MainWindow`에서 `FileTreeController`로 트리 관리 메소드 완전 이전:**
    *   다음 메소드들의 핵심 로직을 `MainWindow`에서 **제거**하고, `FileTreeController` 내부에서 모든 관련 작업을 수행하도록 **완전히 이전**하십시오. `MainWindow`는 컨트롤러의 시그널을 받거나, 필요한 경우 컨트롤러의 공개 메소드만 호출합니다.
        *   `_populate_tree_view`: `FileTreeController`가 `QStandardItemModel`을 직접 생성 및 아이템 구성 후, `model_updated_signal(model)`을 발생시킵니다.
        *   `_on_item_changed` (및 관련 내부 로직 `_set_item_checked_state`, `_update_parent_checked_state`): `FileTreeController`가 자신의 모델(`self.tree_model`)의 `itemChanged` 시그널에 `handle_item_change` 슬롯을 직접 연결하여 모든 체크 상태 변경 로직을 내부에서 완결시킵니다. 최종 선택 정보(파일 수, 폴더 수, 체크된 아이템 Set)는 `selection_changed_signal`로 `MainWindow`에 전달합니다.
        *   `_get_item_path`: `FileTreeController` 내부 유틸리티 메소드로 완전히 이전합니다.
        *   `_update_check_stats`: `FileTreeController` 내부에서 선택 상태 변경 후 호출되며, 결과는 `selection_changed_signal`에 포함하여 전달합니다.
        *   `_find_item_by_path`: `FileTreeController` 내부 유틸리티 메소드로 완전히 이전합니다.

3.  **`FileTreeController.selection_changed_signal` 인자 변경:**
    *   시그널 정의를 `selection_changed_signal = Signal(int, int, set)`으로 변경하여, 선택된 파일 수, 선택된 폴더 수, 그리고 **체크된 아이템 경로 `set` 자체**를 전달하도록 수정하십시오.

**II. `MainWindow` 역할 재정의 및 UI 업데이트 로직 명확화 (`src/gui/main_window.py`)**

1.  **`MainWindow`의 상태 변수 참조 방식 변경:**
    *   `MainWindow` 내에서 (이전된) `checked_files`, `checked_dirs`, `checked_items` 등의 상태 변수를 직접 참조하는 대신, `FileTreeController`의 `selection_changed_signal`로부터 전달받은 값을 사용하거나, 필요한 경우 `FileTreeController`의 getter 메소드를 호출하여 UI 업데이트에 사용하도록 수정하십시오.

2.  **`_on_selection_changed` 슬롯 로직 수정:**
    *   `FileTreeController.selection_changed_signal(files_count, dirs_count, checked_items_set)` 시그널을 받도록 슬롯의 인자를 수정하십시오.
    *   전달받은 `checked_items_set`을 사용하여 `TokenController`에 토큰 계산을 위한 파일 목록을 전달하십시오. `MainWindow`가 `FileTreeController.get_checked_items()`를 다시 호출할 필요가 없습니다.

3.  **`_on_item_clicked` 및 `_on_item_double_clicked` 메소드 정리:**
    *   `_on_item_clicked`: `CustomTreeView.item_clicked` 시그널 연결 및 해당 메소드를 `MainWindow`에서 **제거**하십시오. 파일 아이템 클릭 시 체크 상태 토글은 `CustomTreeView.mouseReleaseEvent` 또는 `FileTreeController.handle_item_change`에서 이미 처리되어야 합니다. (중복 로직 제거)
    *   `_on_item_double_clicked`: 폴더 아이템 더블 클릭 시 확장/축소 로직을 `CustomTreeView.mouseDoubleClickEvent` (현재는 `event.accept()`로 무시) 또는 `CustomTreeView.mouseReleaseEvent` 내에서 직접 처리하거나, `FileTreeController`가 모델의 확장 상태를 변경하는 방식으로 수정하십시오. `MainWindow`에 해당 로직이 남아있지 않도록 합니다.

4.  **`_connect_events` 메소드 내 트리 뷰 시그널 연결 위치 변경:**
    *   `tree_view.expanded.connect(self._on_item_expanded)` 및 `tree_view.collapsed.connect(self._on_item_collapsed)` 연결을 `MainWindow`에서 **제거**하십시오.
    *   대신, `LeftPanelWidget.__init__` 내부에서 `self.tree_view.expanded.connect(self.update_item_icon_on_expand)` 와 같이 `LeftPanelWidget` 자체 메소드에 직접 연결하도록 수정하십시오. (`update_item_icon_on_expand`는 `update_item_icon`을 적절히 호출하는 새 메소드일 수 있습니다.)

**III. 아이콘 관리 및 주입 방식 일관성 확보 (`src/gui/main_window.py`, `src/gui/panels.py`, `src/gui/controllers.py`)**

1.  **`LeftPanelWidget` 아이콘 주입 최적화:**
    *   `FileTreeController._populate_tree_view`에서 모든 파일/폴더 아이템의 아이콘을 설정하므로, `LeftPanelWidget`은 디렉토리 확장/축소 시 아이콘 변경에 필요한 `folder_icon`과 `folder_open_icon`만 생성자에서 주입받도록 수정하십시오. 다른 파일 타입별 아이콘 인자는 `LeftPanelWidget` 생성자에서 **제거**합니다.
    *   `FileTreeController` 생성자에는 `_populate_tree_view`에서 필요한 모든 아이콘(파일 타입별 아이콘 포함)이 주입되도록 유지합니다.

**IV. 메뉴 액션 상태 초기화 동기화 (`src/gui/main_window.py`, `src/gui/controllers.py`)**

1.  **메뉴 액션 초기 상태 설정:**
    *   `MainWindow._create_menu`에서 `self.show_hidden_action`과 `self.gitignore_filter_action`의 초기 체크 상태를 `FileTreeController`의 `self.show_hidden` 및 `self.apply_gitignore_rules` 변수의 초기값과 동일하게 설정하십시오.
    *   이를 위해 `MainWindow`가 `FileTreeController` 생성 후 해당 초기 상태 값을 getter를 통해 가져와 메뉴 아이템에 반영하도록 수정합니다.

**V. (선택 사항) 마지막 사용 디렉토리 로드 기능 (`src/gui/main_window.py`, `src/utils/settings_manager.py`)**

1.  **마지막 디렉토리 저장:** 애플리케이션 종료 시 또는 폴더 변경 시 `SettingsManager`를 사용하여 현재 `current_folder`를 저장하도록 `MainWindow`에 로직을 추가하십시오.
2.  **마지막 디렉토리 로드:** `MainWindow.show()` 또는 `__init__`에서 `SettingsManager`로부터 마지막으로 사용한 디렉토리를 불러와, `os.getcwd()` 대신 해당 디렉토리로 초기 폴더를 로드하도록 수정하십시오.

---

**최종 검증:**

*   위 모든 지시사항 적용 후, 애플리케이션의 모든 기능(폴더 열기, 파일 선택/해제 및 올바른 수량/토큰 표시, 아이콘 변경, 클립보드 복사, 메뉴 옵션(숨김 파일, gitignore 필터) 토글 기능의 정확성을 집중적으로 검증하십시오.
*   콘솔 및 로그 파일(`app.log`)을 확인하여 새로운 오류나 경고가 없는지, 그리고 로깅이 의도대로 동작하는지 확인하십시오.
*   `MainWindow`의 코드가 이전보다 간결해지고, 각 클래스의 역할과 책임이 더욱 명확하게 분리되었는지 주관적으로 평가하십시오.