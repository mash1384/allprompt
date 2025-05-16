# LLM 프롬프트 헬퍼 패키지 요약

이 문서는 LLM 프롬프트 헬퍼의 패키징 구성 요소와 빠른 시작 가이드를 제공합니다.

## 패키징 구성 요소

LLM 프롬프트 헬퍼 프로젝트는 다음과 같은 방식으로 패키징되었습니다:

1. **Python 패키지**
   - `setup.py`: 기본 설정 파일
   - `setup.cfg`: 패키지 메타데이터와 설정
   - `pyproject.toml`: 빌드 시스템 요구사항
   - `MANIFEST.in`: 패키지에 포함할 추가 파일 지정

2. **Docker 컨테이너**
   - `Dockerfile`: Docker 이미지 빌드 설정

3. **실행 파일 (PyInstaller)**
   - `llm-prompt-helper.spec`: PyInstaller 빌드 설정

## 빠른 시작 가이드

### Python 패키지로 설치하기

```bash
# 패키지 빌드
python -m build

# 로컬에서 설치
pip install dist/llm_prompt_helper-0.1.0-py3-none-any.whl

# 실행
llm-prompt-helper
```

### Docker로 실행하기

```bash
# Docker 이미지 빌드
docker build -t llm-prompt-helper .

# Docker 컨테이너 실행
docker run -it --rm llm-prompt-helper
```

### 실행 파일 만들기

```bash
# PyInstaller 설치
pip install pyinstaller

# 실행 파일 빌드
pyinstaller llm-prompt-helper.spec

# 실행 파일은 dist/ 디렉토리에 생성됩니다
# Windows: dist/llm-prompt-helper.exe
# macOS: dist/LLM Prompt Helper.app
# Linux: dist/llm-prompt-helper
```

## 패키징 파일 구조

```
LLM-프롬프트-헬퍼/
├── setup.py              # 기본 패키지 설정
├── setup.cfg             # 패키지 메타데이터와 옵션
├── pyproject.toml        # 빌드 시스템 설정
├── MANIFEST.in           # 추가 포함 파일 지정
├── Dockerfile            # Docker 이미지 설정
├── llm-prompt-helper.spec # PyInstaller 설정
├── PACKAGING.md          # 패키징 상세 가이드
└── PACKAGE-README.md     # 이 파일
```

자세한 패키징 과정은 `PACKAGING.md` 파일을 참조하세요.

## 주의사항

- 프로덕션 환경에 배포하기 전에 패키지의 버전 관리 및 업데이트 메커니즘을 고려하세요.
- 보안 업데이트 및 의존성 관리 전략을 수립하세요.
- 사용자 피드백을 수집하고 지속적으로 개선할 수 있는 방법을 마련하세요. 