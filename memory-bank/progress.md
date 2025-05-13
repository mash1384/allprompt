# 프로젝트 진행 기록

## Phase 0: 준비 및 설계

### 단계 1: 개발 환경 설정
- Python 3.8 이상 설치 확인
- pip 설치 확인
- 프로젝트 디렉토리 생성 
- 가상 환경 생성 준비

### 단계 2: 핵심 의존성 설치 (완료)
- 다음 핵심 의존성을 포함한 requirements.txt 파일 생성:
  - PySide6>=6.5.0: GUI 프레임워크
  - tiktoken>=0.5.1: OpenAI 토큰화 라이브러리
  - pathspec>=0.11.0: .gitignore 패턴 적용
  - pyperclip>=1.8.2: 클립보드 제어
  - requests>=2.31.0: HTTP 요청 처리
  - packaging>=23.0: 버전 문자열 처리
  - appdirs>=1.4.4: 플랫폼별 디렉토리 경로 관리

- 프로젝트 구조 생성:
  - src/: 소스 코드 디렉토리
    - core/: 핵심 로직 모듈 (file_scanner.py, tokenizer.py, filter.py, output_formatter.py)
    - gui/: 사용자 인터페이스 모듈 (main_window.py, settings_dialog.py)
    - utils/: 유틸리티 모듈 (settings_manager.py, clipboard_utils.py)
  - tests/: 테스트 코드 디렉토리
  - venv/: 가상 환경 디렉토리
  
- 핵심 모듈 파일 구현:
  - file_scanner.py: 디렉토리 스캔, 파일 유형 감지, 텍스트 파일 읽기
  - tokenizer.py: 토큰 수 계산 및 모델 관리
  - filter.py: .gitignore 규칙 파싱 및 적용
  - output_formatter.py: 선택된 파일의 내용을 형식화된 출력으로 변환
  - main_window.py: 메인 UI 레이아웃, 트리 뷰, 버튼 구성
  - settings_dialog.py: 사용자 설정 관리 UI
  - settings_manager.py: 설정 저장 및 로드
  - clipboard_utils.py: 클립보드 복사 및 붙여넣기

- 기타 관리 파일 생성:
  - README.md: 프로젝트 소개, 설치 및 사용법 가이드
  - .gitignore: 버전 관리에서 제외될 파일 패턴 정의
