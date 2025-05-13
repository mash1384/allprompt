#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
리소스 컴파일 스크립트
.qrc 파일을 Python 모듈로 컴파일합니다.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def find_resource_compiler():
    """PySide6 또는 PyQt6의 리소스 컴파일러 경로를 찾습니다."""
    
    # 우선순위: pyside6-rcc > pyrcc6 > pyside2-rcc > pyrcc5
    possible_compilers = [
        "pyside6-rcc",
        "pyrcc6",
        "pyside2-rcc",
        "pyrcc5"
    ]
    
    for compiler in possible_compilers:
        if shutil.which(compiler):
            return compiler
    
    return None

def compile_resources(qrc_file="resources.qrc", output_file="resources.py"):
    """리소스 파일을 컴파일합니다."""
    
    # 현재 스크립트 디렉토리 경로
    current_dir = Path(__file__).parent.absolute()
    
    # 입출력 파일의 절대 경로
    qrc_path = current_dir / qrc_file
    output_path = current_dir / output_file
    
    if not qrc_path.exists():
        print(f"오류: {qrc_path} 파일을 찾을 수 없습니다.")
        return False
    
    # 리소스 컴파일러 찾기
    compiler = find_resource_compiler()
    if not compiler:
        print("오류: 리소스 컴파일러를 찾을 수 없습니다. PySide6 또는 PyQt6가 설치되어 있는지 확인하세요.")
        return False
    
    # 컴파일 명령 구성
    cmd = [compiler, str(qrc_path), "-o", str(output_path)]
    
    try:
        # 컴파일 실행
        subprocess.run(cmd, check=True)
        print(f"성공: {qrc_path} 파일이 {output_path}로 컴파일되었습니다.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"오류: 리소스 컴파일 중 문제가 발생했습니다: {e}")
        return False

if __name__ == "__main__":
    result = compile_resources()
    sys.exit(0 if result else 1) 