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

# src.core.file_scanner 경로가 올바른지 확인 (PyInstaller 패키징 시 중요)
# 현재 파일 위치가 src/core/ 이므로, 같은 레벨의 file_scanner를 직접 임포트
from .file_scanner import read_text_file
# 만약 이 파일이 다른 위치에서 실행되거나 import 구조가 다르다면,
# from src.core.file_scanner import read_text_file 와 같이 프로젝트 루트 기준 경로 사용

from src.core.constants import EXTENSION_TO_LANGUAGE_MAP

logger = logging.getLogger(__name__)

def generate_file_map(
    items: List[Dict[str, Any]],
    root_path: Union[str, Path],
    indent_size: int = 2 # indent_size는 현재 _traverse_tree에서 직접 사용되진 않음 (공백으로 고정)
) -> str:
    """
    선택된 파일 및 폴더 구조를 <file_map> 형식으로 변환
    트리 구조 문자(├──, └──, │)를 사용하여 직관적인 파일 구조 표현

    Args:
        items: 파일 및 폴더 정보 목록 (체크된 항목만, 'rel_path', 'is_dir' 포함)
        root_path: 루트 디렉토리 경로
        indent_size: 들여쓰기 공백 수 (현재 미사용, _traverse_tree 내부에서 고정된 공백 사용)

    Returns:
        <file_map> 형식의 문자열
    """
    root_path = Path(root_path)
    root_name = root_path.name

    if not root_name: # 루트 경로가 '.' 등으로 이름이 없는 경우
        root_name = "project_root" # 기본 이름 사용

    lines = [f"<file_map>", f"{root_name}/"]

    # 경로 기준으로 정렬 (Path 객체로 변환하여 정렬해야 올바른 순서 보장)
    sorted_items = sorted(items, key=lambda x: Path(x.get('rel_path', '')))

    logger.debug(f"generate_file_map: {len(sorted_items)}개 항목으로 맵 생성 시작 (루트: {root_name})")

    # 임시 디렉토리 트리 구성 (원본 로직 유지)
    tree = {}
    for item in sorted_items:
        if 'rel_path' not in item:
            logger.warning(f"rel_path가 없는 항목 발견 (건너뜀): {item.get('path', '알 수 없는 경로')}")
            continue

        rel_path = item['rel_path']
        # 경로 타입 확인 및 변환
        if not isinstance(rel_path, Path):
            rel_path = Path(str(rel_path))

        # 루트 항목 자체(rel_path == Path('.'))는 트리의 시작점이므로, 그 하위로 구성
        if rel_path == Path('.'):
            logger.debug(f"루트 항목({item.get('path')})은 맵의 기준으로 사용, 트리에는 직접 추가 안 함.")
            continue

        is_dir = item.get('is_dir', False)
        logger.debug(f"맵 트리 구성 중 - 항목 처리: {rel_path}, is_dir: {is_dir}")

        parts = list(rel_path.parts)
        parts = [p for p in parts if p and p != '.'] # 유효한 부분만 필터링

        if not parts:
            logger.warning(f"유효한 경로 부분이 없는 항목 (건너뜀): {rel_path}")
            continue

        # 트리에 항목 추가 (원본 로직과 유사하게)
        current_level_dict = tree
        for i, part_name in enumerate(parts):
            is_last_part_of_path = (i == len(parts) - 1)
            if is_last_part_of_path:
                # 마지막 부분이면, 디렉토리면 빈 딕셔너리, 파일이면 True (또는 다른 마커)
                current_level_dict[part_name] = {} if is_dir else True # 디렉토리는 자식을 가질 수 있음
            else:
                # 중간 디렉토리면 딕셔너리 추가 또는 기존 딕셔너리 사용
                # 만약 이전에 파일로 기록된 경로에 하위 항목이 생기면 디렉토리로 변경
                if part_name not in current_level_dict or not isinstance(current_level_dict[part_name], dict):
                    current_level_dict[part_name] = {}
                current_level_dict = current_level_dict[part_name]

    # 트리를 문자열로 변환하는 재귀 함수 (원본 로직 유지)
    def _traverse_tree(node_dict, parent_prefix=""):
        # 함수 내부에서 사용할 리스트 (lines는 외부 스코프 변수이므로 직접 사용하지 않음)
        local_lines = []
        
        # None 체크 추가 (원본에 없었으나, 안전을 위해)
        if node_dict is None or not isinstance(node_dict, dict):
            return local_lines

        # 이름순으로 정렬된 아이템 리스트 (원본과 동일)
        # 디렉토리와 파일을 구분하여 정렬하거나, OS 기본 정렬을 따를 수 있음.
        # 여기서는 단순 이름순 정렬.
        dict_items_sorted = sorted(node_dict.items())
        num_items_in_level = len(dict_items_sorted)

        for i, (name, value_is_dict_or_true) in enumerate(dict_items_sorted):
            is_last_item_in_this_level = (i == num_items_in_level - 1)

            # 트리 구조 문자 결정 (원본과 동일)
            connector = "└── " if is_last_item_in_this_level else "├── "
            # 현재 라인 생성
            current_line_str = f"{parent_prefix}{connector}{name}"

            is_item_directory = isinstance(value_is_dict_or_true, dict)
            if is_item_directory:
                current_line_str += "/"
            local_lines.append(current_line_str)

            # 자식 노드가 있으면 재귀적으로 처리 (원본과 동일)
            if is_item_directory:
                # 다음 레벨의 prefix 계산
                next_parent_prefix = parent_prefix + ("    " if is_last_item_in_this_level else "│   ")
                local_lines.extend(_traverse_tree(value_is_dict_or_true, next_parent_prefix))
        return local_lines

    if not tree: # 루트 외에 선택된 항목이 없는 경우
        logger.warning(f"{root_name}/ 내에 표시할 선택된 하위 파일 또는 폴더가 없습니다.")
        lines.append("// (선택된 하위 파일 또는 폴더 없음)")
    else:
        lines.extend(_traverse_tree(tree)) # _traverse_tree가 반환하는 리스트를 확장

    lines.append("</file_map>")
    return "\n".join(lines)


def generate_file_contents(
    items: List[Dict[str, Any]], # main_window.py에서 파일 정보만 필터링해서 전달해야 함
    root_path: Union[str, Path]  # 프로젝트 루트 경로
) -> str:
    """
    선택된 파일들의 내용을 <file_contents> 형식으로 변환

    Args:
        items: 파일 정보 목록 (체크된 "파일" 항목만, 'path', 'rel_path' 포함)
        root_path: 루트 디렉토리 경로 (상대 경로 계산 시 기준)

    Returns:
        <file_contents> 형식의 문자열
    """
    project_root_path = Path(root_path) # 일관성을 위해 Path 객체로
    contents_output_lines = ["<file_contents>"] # 변수명 변경 (contents와 구분)

    # items 리스트는 이미 파일들만 포함하고, rel_path 기준으로 정렬되어 있다고 가정.
    # (main_window.py의 _copy_to_clipboard에서 호출 시 이 전처리를 해야 함)
    # 안전을 위해 여기서도 파일만 필터링하고 정렬 시도
    sorted_file_items = sorted(
        [item for item in items if not item.get('is_dir', True) and 'path' in item],
        key=lambda x: Path(x.get('rel_path', x['path'].name))
    )

    for item_info in sorted_file_items:
        file_abs_path = Path(item_info['path']) # 파일의 절대 경로

        # 표시될 상대 경로 (project_root_path 기준)
        try:
            display_relative_path = file_abs_path.relative_to(project_root_path)
        except ValueError: # 만약 project_root_path의 하위가 아니면 (예외 상황)
            display_relative_path = file_abs_path.name # 파일 이름만 사용
        
        display_relative_path_str = str(display_relative_path).replace(os.sep, '/') # OS 독립적 경로

        file_extension = file_abs_path.suffix.lower()
        language_tag = EXTENSION_TO_LANGUAGE_MAP.get(file_extension, "text") # 기본값 "text"

        # 파일 내용 읽기
        read_result = read_text_file(file_abs_path)
        
        content_string_for_output: str
        if isinstance(read_result, dict) and 'error' in read_result:
            # 오류 정보가 포함된 딕셔너리인 경우 (read_text_file의 반환 형식)
            error_type = read_result.get('error_type', 'UnknownError')
            details = read_result.get('details', '파일을 읽을 수 없습니다.')
            logger.warning(f"파일 읽기 오류 ({error_type}): {file_abs_path} - {details}")
            content_string_for_output = f"// 오류: {error_type} - {details}"
        elif read_result is None: # 이전 버전 호환성 또는 예외적인 None 반환
            logger.warning(f"파일 내용을 읽을 수 없음 (None 반환): {file_abs_path}")
            content_string_for_output = "// 파일을 읽을 수 없습니다."
        else:
            # 성공적으로 읽은 문자열인 경우
            content_string_for_output = read_result
        
        # 파일 내용 형식화하여 추가
        contents_output_lines.append(f"File: {display_relative_path_str}")
        contents_output_lines.append(f"```{language_tag}")
        contents_output_lines.append(content_string_for_output)
        contents_output_lines.append("```")
        contents_output_lines.append("")  # 파일 사이 빈 줄 추가

    contents_output_lines.append("</file_contents>")
    
    # *** 수정된 부분: 오직 contents 문자열만 반환 ***
    return "\n".join(contents_output_lines)


def generate_full_output(
    root_path: Union[str, Path],
    # 이 함수는 main_window.py에서 어떻게 호출하느냐에 따라 두 번째 인자가 달라짐.
    # 원본 코드에서는 file_paths: List[str] (파일 절대 경로 리스트)를 받았었음.
    # 하지만 file_map을 정확히 만들려면 디렉토리 정보도 포함된 items가 필요함.
    # 여기서는 selected_items_details (파일+디렉토리 정보 포함 딕셔너리 리스트)를 받는다고 가정하고 수정.
    # 이 변경은 main_window.py의 _copy_to_clipboard 호출부 수정이 반드시 필요함.
    selected_items_details: List[Dict[str, Any]],
    file_cache: Optional[Dict[str, str]] = None, # 현재 read_text_file에서 캐시 처리하므로 미사용 가능성
    indent_size: int = 2
) -> str:
    """
    Generate complete output including both <file_map> and <file_contents>
    
    Args:
        root_path: Root directory path of the project being scanned.
        selected_items_details: List of dictionaries, each representing a selected item
                                (file or directory). Each dict should contain at least
                                'path' (absolute Path object), 'rel_path' (relative Path or str),
                                and 'is_dir' (boolean).
        file_cache: Optional cache for file contents. (Currently not directly used here if
                    read_text_file handles its own caching or doesn't use an external cache.)
        indent_size: Number of spaces for indentation in the file map.
        
    Returns:
        String containing <file_map> and <file_contents> in sequence.
    """
    project_root = Path(root_path)

    # <file_map> 생성: selected_items_details 전체를 사용 (파일 및 디렉토리 정보 포함)
    # generate_file_map은 'rel_path', 'is_dir' 등을 포함하는 딕셔너리 리스트를 기대함.
    file_map_str = generate_file_map(selected_items_details, project_root, indent_size)
    
    # <file_contents> 생성: selected_items_details에서 파일 정보만 필터링하여 전달
    # generate_file_contents는 'path', 'rel_path' 등을 포함하는 파일 아이템 딕셔너리 리스트를 기대함.
    file_items_for_contents = [
        item for item in selected_items_details if not item.get('is_dir', True) and 'path' in item
    ]
    file_contents_str = generate_file_contents(file_items_for_contents, project_root)
    
    # 최종 결과 조합
    final_output_str = f"{file_map_str}\n\n{file_contents_str}"
    
    # (디버깅 로그 - 이전 답변의 제안 유지)
    logger.info(f"Generated full output length: {len(final_output_str)}")
    if final_output_str:
        log_preview = final_output_str[:500].replace('\n', '\\n') # 개행문자 이스케이프
        logger.info(f"Generated full output (first 500 chars, newlines escaped): {log_preview}")
    else:
        logger.warning("Generated full output is empty!")
    
    return final_output_str