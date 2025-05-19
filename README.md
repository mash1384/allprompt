# LLM 프롬프트 헬퍼

LLM 프롬프트용 코드 스니펫을 손쉽게 생성하는 데스크톱 애플리케이션입니다.

## 소개

이 애플리케이션은 코드 폴더를 선택하고 필요한 파일만 포함하여 LLM 프롬프트에 적합한 형식으로 변환해줍니다. 직관적인 인터페이스로 토큰 수를 실시간 확인하면서 `.gitignore` 규칙을 활용해 불필요한 파일을 효율적으로 제외합니다.

## 주요 기능

- 📁 **폴더 구조 시각화** - 트리 뷰로 파일 시스템 탐색
- ✅ **선택적 포함/제외** - 체크박스 및 `.gitignore` 룰 적용
- 🔢 **실시간 토큰 계산** - 선택한 콘텐츠의 토큰 수 표시
- 📋 **표준화된 출력** - `<file_map>` 및 `<file_contents>` 형식
- 🔍 **자동 파일 처리** - 텍스트/바이너리 파일 감지 및 다양한 인코딩 지원

## 다운로드 및 설치

### 배포 버전 (일반 사용자)

[GitHub Releases](https://github.com/yourusername/llm-prompt-helper/releases)에서 다운로드:
- **macOS**: `LLM Prompt Helper.app.zip` 다운로드 후 압축 해제
- **Windows**: `LLM Prompt Helper.exe` 인스톨러 실행

> **참고**: macOS에서 처음 실행 시 "확인되지 않은 개발자" 경고가 표시될 수 있습니다. 시스템 환경설정 > 보안 및 개인 정보 보호에서 허용해주세요.

### 소스에서 설치 (개발자)

```bash
# 1. 저장소 복제
git clone https://github.com/yourusername/llm-prompt-helper.git
cd llm-prompt-helper

# 2. 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 실행
python -m src.main
```

## 사용 방법

1. 애플리케이션 실행
2. **폴더 열기** 버튼 클릭하여 코드 폴더 선택
3. 트리 뷰에서 포함할 파일/폴더 체크
4. 실시간 토큰 수 확인
5. **클립보드에 복사** 버튼 클릭
6. ChatGPT, Claude 등 LLM 프롬프트에 붙여넣기

## 기술적 참고사항

이 프로젝트는 Vibe 코딩 방식으로 개발되었습니다. Vibe 코딩은 빠른 프로토타이핑과 개발에 중점을 둔 방식으로, 일부 기능이나 오류 처리가 완벽하지 않을 수 있습니다. 사용 중 문제가 발생하면 이슈를 등록해주세요.

## 프로젝트 구조

```
src/
├── core/         # 핵심 비즈니스 로직
│   ├── file_scanner.py     # 파일 스캐닝 및 처리
│   ├── filter.py           # 파일 필터링 기능
│   ├── output_formatter.py # 출력 포맷팅
│   ├── tokenizer.py        # 토큰 계산
│   └── sort_utils.py       # 정렬 유틸리티
├── gui/          # 그래픽 사용자 인터페이스
│   ├── main_window.py      # 메인 애플리케이션 창
│   ├── settings_dialog.py  # 설정 대화상자
│   └── resources/          # 아이콘, 스타일시트 등
└── utils/        # 유틸리티 기능
    ├── clipboard_utils.py  # 클립보드 관련 기능
    └── settings_manager.py # 설정 관리
```

## 라이선스

[MIT 라이선스](LICENSE)