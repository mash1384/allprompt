#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
출력 포맷팅 모듈
선택된 파일 및 폴더를 정의된 <file_map>, <file_contents> 형식으로 변환합니다.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from core.file_scanner import read_text_file

logger = logging.getLogger(__name__)

# 파일 확장자에 따른 언어 식별자 매핑
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".json": "json",
    ".md": "markdown",
    ".txt": "text",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".java": "java",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
    ".sql": "sql",
    ".r": "r",
    ".dart": "dart",
    ".lua": "lua",
    ".pl": "perl",
    ".pm": "perl",
    ".hs": "haskell",
}

def generate_file_map(
    items: List[Dict[str, Any]], 
    root_path: Union[str, Path],
    indent_size: int = 2
) -> str:
    """
    선택된 파일 및 폴더 구조를 <file_map> 형식으로 변환
    
    Args:
        items: 파일 및 폴더 정보 목록 (체크된 항목만)
        root_path: 루트 디렉토리 경로
        indent_size: 들여쓰기 공백 수 (기본값: 2)
        
    Returns:
        <file_map> 형식의 문자열
    """
    root_path = Path(root_path)
    root_name = root_path.name
    
    # 루트 경로 없으면 현재 디렉토리 이름 사용
    if not root_name:
        root_name = "project"
    
    lines = [f"<file_map>", f"{root_name}/"]
    
    # 경로 기준으로 정렬
    sorted_items = sorted(items, key=lambda x: str(x.get('rel_path', '')))
    
    # 임시 디렉토리 트리 구성
    tree = {}
    for item in sorted_items:
        if 'rel_path' not in item or item.get('rel_path') == Path('.'):
            continue
            
        rel_path = item['rel_path']
        is_dir = item.get('is_dir', False)
        
        # 경로를 부모 디렉토리 목록으로 변환
        parts = list(rel_path.parts)
        
        # 트리에 항목 추가
        current = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # 마지막 부분이면 리프 노드 추가
                current[part] = None if is_dir else True
            else:
                # 중간 디렉토리면 딕셔너리 추가
                if part not in current:
                    current[part] = {}
                current = current[part]
    
    # 트리를 문자열로 변환
    def _traverse_tree(node, prefix="", depth=1):
        result = []
        for name, value in sorted(node.items()):
            indent = " " * (indent_size * depth)
            if value is None:  # 디렉토리
                result.append(f"{indent}{name}/")
            elif isinstance(value, dict):  # 중간 디렉토리
                result.append(f"{indent}{name}/")
                result.extend(_traverse_tree(value, f"{prefix}{name}/", depth + 1))
            else:  # 파일
                result.append(f"{indent}{name}")
        return result
    
    lines.extend(_traverse_tree(tree))
    lines.append("</file_map>")
    
    return "\n".join(lines)

def generate_file_contents(
    items: List[Dict[str, Any]], 
    root_path: Union[str, Path]
) -> str:
    """
    선택된 파일들의 내용을 <file_contents> 형식으로 변환
    
    Args:
        items: 파일 정보 목록 (체크된 파일만)
        root_path: 루트 디렉토리 경로
        
    Returns:
        <file_contents> 형식의 문자열
    """
    root_path = Path(root_path)
    contents = ["<file_contents>"]
    
    # 경로 기준으로 정렬
    sorted_items = sorted(
        [item for item in items if not item.get('is_dir', True)], 
        key=lambda x: str(x.get('rel_path', ''))
    )
    
    for item in sorted_items:
        if 'path' not in item or item.get('is_dir', True):
            continue
            
        file_path = item['path']
        rel_path = item.get('rel_path', file_path.name)
        
        # 상대 경로 문자열 변환 (OS 독립적 표현)
        rel_path_str = str(rel_path).replace(os.sep, '/')
        
        # 파일 확장자에 따른 언어 식별자 결정
        file_ext = file_path.suffix.lower()
        language = EXTENSION_TO_LANGUAGE.get(file_ext, "text")
        
        # 파일 내용 읽기
        content = read_text_file(file_path)
        if content is None:
            logger.warning(f"파일 내용을 읽을 수 없음: {file_path}")
            content = "// 파일을 읽을 수 없습니다."
        
        # 파일 내용 형식화하여 추가
        contents.append(f"File: {rel_path_str}")
        contents.append(f"```{language}")
        contents.append(content)
        contents.append("```")
        contents.append("")  # 파일 사이 빈 줄 추가
    
    contents.append("</file_contents>")
    
    return "\n".join(contents)

def generate_full_output(
    items: List[Dict[str, Any]], 
    root_path: Union[str, Path],
    indent_size: int = 2
) -> str:
    """
    <file_map>과 <file_contents>를 모두 포함한 전체 출력 생성
    
    Args:
        items: 파일 및 폴더 정보 목록 (체크된 항목만)
        root_path: 루트 디렉토리 경로
        indent_size: 들여쓰기 공백 수 (기본값: 2)
        
    Returns:
        <file_map>과 <file_contents>를 순서대로 포함한 문자열
    """
    file_map = generate_file_map(items, root_path, indent_size)
    file_contents = generate_file_contents(items, root_path)
    
    return f"{file_map}\n\n{file_contents}" 