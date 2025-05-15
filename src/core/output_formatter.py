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

from src.core.file_scanner import read_text_file

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
    트리 구조 문자(├──, └──, │)를 사용하여 직관적인 파일 구조 표현
    
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
    
    # 로깅 추가
    logger.debug(f"generate_file_map: {len(sorted_items)}개 항목 처리 시작")
    
    # 임시 디렉토리 트리 구성
    tree = {}
    for item in sorted_items:
        if 'rel_path' not in item:
            logger.warning(f"rel_path가 없는 항목 발견: {item}")
            continue
            
        rel_path = item['rel_path']
        # 경로 타입 확인 및 변환
        if not isinstance(rel_path, Path):
            rel_path = Path(str(rel_path))
            
        # 루트 항목 건너뛰기
        if rel_path == Path('.'):
            logger.debug("루트 항목 건너뛰기")
            continue
            
        is_dir = item.get('is_dir', False)
        
        # 로깅 추가
        logger.debug(f"항목 처리: {rel_path}, is_dir: {is_dir}")
        
        # 경로를 부모 디렉토리 목록으로 변환
        parts = list(rel_path.parts)
        
        # 유효한 부분만 필터링
        parts = [p for p in parts if p and p != '.']
        
        if not parts:
            logger.warning(f"유효한 경로 부분이 없는 항목: {rel_path}")
            continue
        
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
                
                # 이 부분에서 None 체크 추가
                next_level = current[part]
                if next_level is None:
                    # 이전에 디렉토리로 표시되었다면 딕셔너리로 변경
                    current[part] = {}
                    next_level = current[part]
                elif not isinstance(next_level, dict):
                    # 이미 파일로 표시된 경우 -> 딕셔너리로 변환
                    current[part] = {}
                    next_level = current[part]
                
                current = next_level
    
    # 트리를 문자열로 변환
    def _traverse_tree(node, prefix="", is_last=False, parent_prefix=""):
        result = []
        
        # None 체크 추가
        if node is None:
            return result
            
        if not isinstance(node, dict):
            return result
        
        items = sorted(node.items())
        num_items = len(items)
        
        for i, (name, value) in enumerate(items):
            is_last_item = (i == num_items - 1)
            
            # 트리 구조 문자 결정
            if is_last_item:
                connector = "└── "
                next_prefix = parent_prefix + "    "
            else:
                connector = "├── "
                next_prefix = parent_prefix + "│   "
            
            # 현재 라인 생성
            current_line = f"{parent_prefix}{connector}{name}"
            if value is None or isinstance(value, dict):  # 디렉토리
                current_line += "/"
            
            result.append(current_line)
            
            # 자식 노드가 있으면 재귀적으로 처리
            if isinstance(value, dict):
                child_result = _traverse_tree(
                    value,
                    prefix=prefix + name + "/",
                    is_last=is_last_item,
                    parent_prefix=next_prefix
                )
                result.extend(child_result)
                
        return result
    
    # 트리가 비어있는 경우 처리
    if not tree:
        logger.warning("생성된 트리가 비어 있습니다.")
        lines.append("// 선택된 항목이 없거나 처리할 수 없습니다.")
    else:
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
        result = read_text_file(file_path)
        
        # 새로운 반환 형식 처리 (문자열 또는 딕셔너리)
        if isinstance(result, dict) and 'error' in result:
            # 오류 정보가 포함된 딕셔너리인 경우
            error_type = result.get('error_type', 'UnknownError')
            details = result.get('details', '파일을 읽을 수 없습니다.')
            logger.warning(f"파일 읽기 오류 ({error_type}): {file_path} - {details}")
            content = f"// 오류: {error_type} - {details}"
        elif result is None:
            # None인 경우 (이전 버전 호환성)
            logger.warning(f"파일 내용을 읽을 수 없음: {file_path}")
            content = "// 파일을 읽을 수 없습니다."
        else:
            # 성공적으로 읽은 문자열인 경우
            content = result
        
        # 파일 내용 형식화하여 추가
        contents.append(f"File: {rel_path_str}")
        contents.append(f"```{language}")
        contents.append(content)
        contents.append("```")
        contents.append("")  # 파일 사이 빈 줄 추가
    
    contents.append("</file_contents>")
    
    return f"{file_map}\n\n{'\n'.join(contents)}"

def generate_full_output(
    root_path: Union[str, Path], 
    file_paths: List[str],
    file_cache: Dict[str, str] = None,
    indent_size: int = 2
) -> str:
    """
    Generate complete output including both <file_map> and <file_contents>
    
    Args:
        root_path: Root directory path
        file_paths: List of file paths to include
        file_cache: Cache of file contents {file_path: content}
        indent_size: Number of spaces for indentation (default: 2)
        
    Returns:
        String containing <file_map> and <file_contents> in sequence
    """
    # Convert paths to item dictionaries for compatibility with existing functions
    root_path = Path(root_path)
    items = []
    
    for path_str in file_paths:
        path = Path(path_str)
        # Calculate relative path from root
        try:
            rel_path = path.relative_to(root_path)
        except ValueError:
            # If not relative to root, use filename only
            rel_path = Path(path.name)
            
        items.append({
            'path': path,
            'rel_path': rel_path,
            'is_dir': path.is_dir()
        })
    
    # Generate file map
    file_map = generate_file_map(items, root_path, indent_size)
    
    # Generate file contents with file cache if provided
    contents = ["<file_contents>"]
    
    # Sort files by path
    sorted_items = sorted(
        [item for item in items if not item.get('is_dir', True)], 
        key=lambda x: str(x.get('rel_path', ''))
    )
    
    for item in sorted_items:
        if 'path' not in item or item.get('is_dir', True):
            continue
            
        file_path = item['path']
        rel_path = item.get('rel_path', file_path.name)
        
        # Convert relative path to string (OS-independent representation)
        rel_path_str = str(rel_path).replace(os.sep, '/')
        
        # Determine language identifier based on file extension
        file_ext = file_path.suffix.lower()
        language = EXTENSION_TO_LANGUAGE.get(file_ext, "text")
        
        # Get file content from cache if available, otherwise read from file
        if file_cache and str(file_path) in file_cache:
            content = file_cache[str(file_path)]
        else:
            # Read file content
            result = read_text_file(file_path)
            
            # Handle different return formats (string or dictionary)
            if isinstance(result, dict) and 'error' in result:
                # Dictionary with error information
                error_type = result.get('error_type', 'UnknownError')
                details = result.get('details', 'Unable to read file.')
                logger.warning(f"File reading error ({error_type}): {file_path} - {details}")
                content = f"// Error: {error_type} - {details}"
            elif result is None:
                # None case (for backward compatibility)
                logger.warning(f"Unable to read file content: {file_path}")
                content = "// File could not be read."
            else:
                # Successfully read string
                content = result
        
        # Format file content and add to output
        contents.append(f"File: {rel_path_str}")
        contents.append(f"```{language}")
        contents.append(content)
        contents.append("```")
        contents.append("")  # Add empty line between files
    
    contents.append("</file_contents>")
    
    return f"{file_map}\n\n{'\n'.join(contents)}" 