# LLM 프롬프트 헬퍼

LLM(대규모 언어 모델) 프롬프트에 사용할 코드 스니펫을 쉽게 생성하는 데스크톱 애플리케이션입니다.

## 소개

이 애플리케이션은 로컬 컴퓨터의 코드 폴더나 파일을 선택하여 그 구조와 내용을 LLM 프롬프트에 적합한 형식으로 쉽게 복사할 수 있도록 도와줍니다. 직관적인 GUI를 통해 원하는 파일 및 폴더를 선택하고, `.gitignore` 규칙을 적용하여 불필요한 파일을 효율적으로 제외하며, 선택된 콘텐츠의 총 LLM 토큰 수를 실시간으로 확인할 수 있습니다.

## 주요 기능

- **폴더 구조 시각화**: 로컬 폴더의 파일 및 하위 폴더 구조를 트리 뷰로 표시
- **선택적 포함/제외**: 체크박스로 개별 항목 선택 및 `.gitignore` 규칙 자동 적용
- **실시간 토큰 계산**: 선택된 파일의 총 토큰 수를 실시간으로 표시
- **표준화된 출력 형식**: `<file_map>` 및 `<file_contents>` 형식으로 클립보드에 복사
- **다양한 파일 처리**: 텍스트/바이너리 파일 자동 감지, 다양한 인코딩 지원

## 설치 방법

### 요구 사항

- Python 3.8 이상
- 아래 패키지 의존성:
  - PySide6
  - tiktoken
  - pathspec
  - pyperclip
  - requests
  - packaging
  - appdirs

### 설치 과정

1. 저장소 클론:
   ```
   git clone https://github.com/yourusername/llm-prompt-helper.git
   cd llm-prompt-helper
   ```

2. 가상 환경 생성 및 활성화:
   ```
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. 의존성 설치:
   ```
   pip install -r requirements.txt
   ```

## 사용 방법

1. 애플리케이션 실행:
   ```
   python -m src.main
   ```

2. "폴더 열기" 버튼을 클릭하여 코드 폴더 선택
3. 트리 뷰에서 LLM 프롬프트에 포함할 파일/폴더 체크박스 선택
4. 실시간으로 업데이트되는 토큰 수 확인
5. "클립보드에 복사" 버튼을 클릭하여 형식화된 코드 스니펫 복사
6. 복사된 내용을 LLM 프롬프트에 붙여넣기

## 출력 형식

애플리케이션은 다음과 같은 형식으로 출력을 생성합니다:

1. `<file_map>`: 선택된 파일 및 폴더의 계층 구조
2. `<file_contents>`: 각 파일의 내용 (파일 경로, 언어 식별자, 코드 블록 포함)

## 라이선스

[MIT 라이선스](LICENSE) 

cd /Users/minjihun/allprompt/dist/"LLM Prompt Helper.app"/Contents/MacOS/
./"LLM Prompt Helper"