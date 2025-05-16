# LLM 프롬프트 헬퍼 패키징 가이드

이 문서는 LLM 프롬프트 헬퍼를 패키징하고 배포하는 방법을 설명합니다.

## 필요한 도구 설치

패키징과 배포를 위해 필요한 도구를 설치합니다:

```bash
pip install --upgrade pip
pip install build twine wheel
```

## 패키지 빌드

### 소스 배포판과 휠 빌드하기

다음 명령어를 실행하여 소스 배포판과 휠을 빌드합니다:

```bash
python -m build
```

이 명령은 `dist/` 디렉토리에 다음 파일들을 생성합니다:
- `llm-prompt-helper-0.1.0.tar.gz` (소스 배포판)
- `llm_prompt_helper-0.1.0-py3-none-any.whl` (휠)

## 패키지 테스트

### 로컬에서 패키지 설치 테스트

빌드된 패키지를 로컬에서 테스트하려면 다음 명령어를 실행합니다:

```bash
pip install dist/llm_prompt_helper-0.1.0-py3-none-any.whl
```

설치 후 다음 명령어로 실행할 수 있습니다:

```bash
llm-prompt-helper
```

또는:

```bash
python -m src.main
```

### 패키지 제거

테스트 후 패키지를 제거하려면:

```bash
pip uninstall llm-prompt-helper
```

## PyPI 배포

### TestPyPI에 배포 (테스트 목적)

먼저 TestPyPI에 배포하여 테스트해 볼 수 있습니다:

```bash
python -m twine upload --repository testpypi dist/*
```

TestPyPI에서 설치:

```bash
pip install --index-url https://test.pypi.org/simple/ llm-prompt-helper
```

### 실제 PyPI에 배포

패키지를 실제 PyPI에 배포하려면:

```bash
python -m twine upload dist/*
```

## 실행 파일 만들기 (선택사항)

### PyInstaller를 사용하여 실행 파일 생성

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name llm-prompt-helper --icon=icon.ico src/main.py
```

실행 파일은 `dist/` 디렉토리에 생성됩니다.

## Docker 이미지 빌드 (선택사항)

### Dockerfile 생성

프로젝트 루트 디렉토리에 `Dockerfile`을 생성하고 다음과 같이 작성합니다:

```
FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -e .

CMD ["llm-prompt-helper"]
```

### Docker 이미지 빌드

```bash
docker build -t llm-prompt-helper .
```

### Docker 컨테이너 실행

```bash
docker run -it --rm llm-prompt-helper
```

## 주의사항

- 릴리스 전에 버전 번호를 업데이트해야 합니다 (`src/__init__.py`의 `__version__` 변수).
- PyPI에 배포하기 전에 패키지 이름이 사용 가능한지 확인하세요.
- 실제 배포 전에 TestPyPI에서 먼저 테스트하는 것이 좋습니다. 