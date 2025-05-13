# LLM 프롬프트 헬퍼: 아키텍처 문서

## 프로젝트 구조

```
프로젝트 루트/
├── src/                    # 소스 코드 디렉토리
│   ├── __init__.py         # 패키지 초기화
│   ├── main.py             # 애플리케이션 진입점
│   ├── core/               # 핵심 로직 모듈
│   │   ├── __init__.py
│   │   ├── file_scanner.py # 파일 시스템 스캔
│   │   ├── tokenizer.py    # 텍스트 토큰화
│   │   ├── filter.py       # 파일 필터링(.gitignore)
│   │   └── output_formatter.py # 출력 형식화
│   ├── gui/                # GUI 모듈
│   │   ├── __init__.py
│   │   ├── main_window.py  # 메인 윈도우
│   │   └── settings_dialog.py # 설정 다이얼로그
│   └── utils/              # 유틸리티 모듈
│       ├── __init__.py
│       ├── settings_manager.py # 설정 관리
│       └── clipboard_utils.py  # 클립보드 유틸리티
├── tests/                  # 테스트 코드
├── venv/                   # 가상 환경
├── requirements.txt        # 의존성 목록
├── README.md               # 프로젝트 문서
└── .gitignore              # 버전 관리 제외 패턴
```

## 주요 모듈 역할 및 관계

### 핵심 로직 모듈 (src/core/)

#### file_scanner.py
- **역할**: 파일 시스템 검색 및 파일 정보 수집
- **주요 기능**:
  - `scan_directory()`: 디렉토리를 재귀적으로 스캔하여 파일 및 폴더 정보 목록 반환
  - `is_hidden()`: 파일/폴더의 숨김 여부 확인
  - `is_binary_file()`: 텍스트/바이너리 파일 구분
  - `read_text_file()`: 텍스트 파일 내용 읽기 (다양한 인코딩 처리)
- **의존 관계**: 독립적 모듈, 외부 의존성 없음

#### tokenizer.py
- **역할**: 텍스트를 LLM 모델 기준 토큰으로 변환 및 토큰 수 계산
- **주요 기능**:
  - `Tokenizer` 클래스: 토큰화 객체 관리
  - `count_tokens()`: 텍스트 토큰 수 계산
  - `get_available_models()`: 사용 가능한 모델 목록 제공
  - `get_model_max_tokens()`: 모델별 최대 토큰 수 제공
- **의존 관계**: tiktoken 라이브러리에 의존

#### filter.py
- **역할**: .gitignore 규칙 기반 파일/폴더 필터링
- **주요 기능**:
  - `GitignoreFilter` 클래스: .gitignore 파싱 및 필터링 관리
  - `should_ignore()`: 특정 경로가 무시되어야 하는지 확인
  - `filter_paths()`: 경로 목록 필터링
- **의존 관계**: pathspec 라이브러리에 의존

#### output_formatter.py
- **역할**: 선택된 파일 및 폴더 정보를 정의된 출력 형식으로 변환
- **주요 기능**:
  - `generate_file_map()`: 파일 구조 맵 생성
  - `generate_file_contents()`: 파일 내용 형식화
  - `generate_full_output()`: 최종 출력 생성
- **의존 관계**: core.file_scanner 모듈에 의존

### GUI 모듈 (src/gui/)

#### main_window.py
- **역할**: 애플리케이션 메인 윈도우 및 UI 구성
- **주요 기능**:
  - `MainWindow` 클래스: 메인 UI 윈도우
  - 트리 뷰, 버튼, 토큰 카운터 UI 구성
  - 폴더 선택 및 로드 기능
- **의존 관계**: PySide6, core 모듈에 의존

#### settings_dialog.py
- **역할**: 애플리케이션 설정 관리 UI
- **주요 기능**:
  - `SettingsDialog` 클래스: 설정 다이얼로그 UI
  - 모델 선택, 파일 필터링 옵션 관리
- **의존 관계**: PySide6, core.tokenizer 모듈에 의존

### 유틸리티 모듈 (src/utils/)

#### settings_manager.py
- **역할**: 애플리케이션 설정 저장 및 로드
- **주요 기능**:
  - `SettingsManager` 클래스: 설정 관리
  - 설정 파일 읽기/쓰기
  - 기본 설정 관리
- **의존 관계**: appdirs 라이브러리에 의존

#### clipboard_utils.py
- **역할**: 클립보드 작업 관리
- **주요 기능**:
  - `copy_to_clipboard()`: 텍스트를 클립보드에 복사
  - `get_from_clipboard()`: 클립보드 내용 가져오기
- **의존 관계**: pyperclip 라이브러리에 의존

### 애플리케이션 진입점 (src/main.py)
- **역할**: 애플리케이션 초기화 및 실행
- **주요 기능**:
  - 로깅 설정
  - QApplication 인스턴스 생성
  - MainWindow 인스턴스 생성 및 표시
- **의존 관계**: PySide6, gui.main_window 모듈에 의존

## 데이터 흐름

1. **사용자 입력**: GUI를 통해 폴더 선택, 파일 체크박스 선택, 복사 버튼 클릭
2. **파일 시스템 접근**: file_scanner가 선택된 폴더를 스캔하여 파일/폴더 정보 수집
3. **필터링**: filter 모듈이 .gitignore 규칙 기반으로 파일 필터링
4. **토큰화**: 선택된 파일의 내용을 tokenizer가 처리하여 토큰 수 계산
5. **출력 생성**: output_formatter가 선택된 파일 정보와 내용을 정의된 형식으로 변환
6. **클립보드 복사**: clipboard_utils가 생성된 출력을 클립보드에 복사
7. **설정 관리**: settings_manager가 사용자 설정을 저장하고 로드

## 기술 스택

- **언어**: Python 3.8+
- **GUI 프레임워크**: PySide6
- **토큰화**: tiktoken
- **파일 필터링**: pathspec
- **클립보드 관리**: pyperclip
- **설정 저장**: appdirs, json
- **HTTP 요청**: requests
- **버전 관리**: packaging
