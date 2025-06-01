#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM 프롬프트용 코드 스니펫 생성 도우미
"""

# 패키지 모듈 경로 설정
import sys
import os
from pathlib import Path

# 현재 패키지 경로를 sys.path에 추가
src_path = Path(__file__).parent.absolute()
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 프로젝트 루트 디렉토리를 sys.path에 추가
root_path = src_path.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

__version__ = "0.1.1" 