FROM python:3.9-slim

WORKDIR /app

# 의존성 설치를 위한 파일 복사
COPY requirements.txt .

# 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 필요시 X11 관련 의존성 설치 (GUI 애플리케이션을 위함)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libx11-xcb1 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xinput0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# 패키지로 설치
RUN pip install --no-cache-dir -e .

# 실행 명령
CMD ["xvfb-run", "-a", "llm-prompt-helper"] 