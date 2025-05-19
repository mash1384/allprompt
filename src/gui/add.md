# 전체 리팩토링 지침

**목표:** 제공된 Python 프로젝트 코드의 가독성, 유지보수성, 일관성을 향상시키고 오류 처리를 개선합니다.
**주의사항:**
1.  모든 코드 변경은 기존 애플리케이션의 모든 기능을 완벽하게 유지하고 정상적으로 동작해야 합니다.
2.  코드 스타일은 기존 프로젝트의 스타일과 일관성을 유지해야 합니다. (예: PEP 8, 기존 명명 규칙 준수)
3.  각 지시사항 적용 후, 애플리케이션을 실행하여 주요 기능(폴더 열기, 파일 선택/해제, 아이콘 표시, 클립보드 복사 등)이 올바르게 작동하는지 반드시 확인하십시오.

---

**세부 리팩토링 지시사항:**

**1. `FileTreeController._populate_tree_view()` 메소드 가독성 향상**

   *   **대상 파일:** `src/gui/controllers.py`
   *   **요청:** `FileTreeController` 클래스의 `_populate_tree_view` 메소드 내부 로직을 다음과 같이 리팩토링하여 가독성을 높여주십시오.
      1.  **아이콘 결정 로직 분리:**
         *   파일 확장자 및 아이템 정보(`is_dir`, `is_symlink`, `error` 등)에 따라 `QStandardItem`의 아이콘을 결정하고 설정하는 부분을 별도의 private 헬퍼 메소드 (예: `_get_item_icon(self, item_info: Dict[str, Any]) -> QIcon`)로 분리하십시오.
         *   `item_info` 딕셔너리는 `scan_directory` 결과의 단일 항목과 유사한 구조를 가집니다.
         *   `_populate_tree_view` 메소드 내에서는 이 헬퍼 메소드를 호출하여 각 아이템의 아이콘을 설정합니다.
      2.  **중간 부모 노드 생성 로직 분리 (필요시):**
         *   아이템의 상대 경로(`rel_path`)를 기준으로 부모 `QStandardItem`을 찾거나, 존재하지 않을 경우 필요한 중간 경로의 부모 `QStandardItem`들을 생성하여 트리에 추가하고 `item_dict`에 등록하는 로직을 별도의 private 헬퍼 메소드 (예: `_ensure_parent_item(self, rel_path: Path, root_item: QStandardItem, item_dict: Dict[Path, QStandardItem]) -> QStandardItem`)로 분리하십시오.
         *   이 메소드는 해당 `rel_path`의 직접적인 부모 `QStandardItem`을 반환해야 합니다.

**2. 상수 및 매핑 정보 중앙 관리**

   *   **2.1. 파일 확장자-언어 매핑 정보 통합**
      1.  **새 파일 생성:** `src/core/constants.py` 파일을 생성하십시오.
      2.  **통합 매핑 정의:** `src/core/constants.py` 파일에 `EXTENSION_TO_LANGUAGE_MAP` 이라는 이름의 통합된 딕셔너리 상수를 정의하십시오. 이 맵은 `src/core/output_formatter.py`의 `EXTENSION_TO_LANGUAGE`와 `src/gui/main_window.py`의 `FILE_EXTENSIONS_TO_LANGUAGE`의 정보를 병합하고 중복을 제거한, 가장 포괄적인 내용을 담아야 합니다.
      3.  **참조 수정:**
         *   `src/core/output_formatter.py`에서 기존 `EXTENSION_TO_LANGUAGE` 대신 `src.core.constants.EXTENSION_TO_LANGUAGE_MAP`을 임포트하여 사용하도록 수정하십시오.
         *   `src/gui/main_window.py`에서 기존 `FILE_EXTENSIONS_TO_LANGUAGE` 정의를 제거하십시오. (현재 `MainWindow`에서 직접 사용되지 않으므로, `FileTreeController`에서 아이콘 결정 시 필요한 경우 `constants`의 맵을 참조하도록 합니다.)

   *   **2.2. `Qt.UserRole` 사용 명확화 (아이템 메타데이터)**
      1.  **새 파일 생성 (또는 기존 파일 사용):** `src/gui/constants.py` 파일 (2.1에서 생성) 또는 `src/gui/controllers.py` 상단 등에 아이템 데이터 관련 사용자 역할 상수를 정의하십시오.
      2.  **역할 상수 정의:** 다음과 같이 `QStandardItem`에 메타데이터를 저장하기 위한 역할을 정의합니다.
         *   `ITEM_DATA_ROLE = Qt.UserRole`
      3.  **데이터 저장 방식 변경:** `FileTreeController._populate_tree_view` 및 관련 메소드에서 `item.setData(Qt.UserRole, True)` (디렉토리 여부) 와 같이 직접 값을 설정하는 대신, `ITEM_DATA_ROLE`을 사용하여 아이템 관련 주요 정보를 딕셔너리 형태로 저장하도록 변경하십시오.
         *   예시: `item_metadata = {'is_dir': info.get('is_dir', False), 'abs_path': str(info.get('path')), 'rel_path': str(info.get('rel_path'))}`
         *   `item.setData(ITEM_DATA_ROLE, item_metadata)`
      4.  **데이터 참조 방식 변경:** `FileTreeController`, `CustomTreeView`, `LeftPanelWidget` 등에서 `item.data(Qt.UserRole)`로 디렉토리 여부 등을 판단하던 로직을 `item.data(ITEM_DATA_ROLE)`로 딕셔너리를 가져온 후, `metadata.get('is_dir')` 와 같이 해당 키로 값을 참조하도록 수정하십시오.

**3. `MainWindow._load_folder` 오류 처리 개선**

   *   **대상 파일:** `src/gui/main_window.py`
   *   **요청:** `MainWindow` 클래스의 `_load_folder` 메소드 내 `try-except` 블록을 다음과 같이 개선하십시오.
      1.  기존 `except Exception as e:` 블록 이전에 `FileNotFoundError`와 `PermissionError`에 대한 `except` 블록을 각각 추가하십시오.
      2.  `FileNotFoundError` 발생 시: `QMessageBox.critical(self, "Error Loading Folder", f"Folder not found: {folder_path}")`와 같이 사용자에게 메시지를 표시합니다.
      3.  `PermissionError` 발생 시: `QMessageBox.critical(self, "Error Loading Folder", f"Permission denied for folder: {folder_path}")`와 같이 사용자에게 메시지를 표시합니다.
      4.  일반 `Exception` 블록은 가장 마지막에 두어, 그 외 예상치 못한 오류를 처리하도록 유지합니다.

**4. `CustomTreeView`의 마우스 이벤트 관련 메소드 가독성 검토**

   *   **대상 파일:** `src/gui/custom_widgets.py`
   *   **요청:** `CustomTreeView` 클래스의 `_is_checkbox_area` 및 `_is_branch_indicator_area` 메소드는 Qt의 스타일 및 레이아웃 계산으로 인해 로직이 다소 복잡합니다.
      1.  두 메소드의 로직을 분석하여, 코드 내에 명확한 주석을 추가하고, 변수명을 더 직관적으로 변경하며, 복잡한 조건문을 단순화하거나 설명하는 주석을 추가하는 등 가독성을 향상시킬 수 있는 부분을 개선해주십시오.
      2.  **주의:** 이 작업은 기능 변경 없이 가독성 향상만을 목표로 합니다. 로직의 핵심적인 변경은 피해주시고, 만약 기능 저하의 위험이 있다고 판단되면 현재 상태를 유지하며 주석 추가만으로 개선해주십시오.

---

**최종 확인:** 모든 변경 사항을 적용한 후, 애플리케이션의 전반적인 동작을 다시 한번 테스트하여 회귀 오류가 없는지 확인하십시오.