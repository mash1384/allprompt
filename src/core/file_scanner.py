#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
파일 시스템 스캔 모듈
폴더 구조를 재귀적으로 스캔하여 파일 및 폴더 목록을 생성합니다.
심볼릭 링크, 숨김 파일/폴더 처리 기능 포함.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional, Union, Any

logger = logging.getLogger(__name__)

def scan_directory(
    root_path: Union[str, Path], 
    follow_symlinks: bool = False,
    include_hidden: bool = False
) -> List[Dict[str, Any]]:
    """
    지정된 디렉토리를 재귀적으로 스캔하여 파일 및 폴더 정보 목록을 반환
    
    Args:
        root_path: 스캔할 루트 디렉토리 경로
        follow_symlinks: 심볼릭 링크를 따라갈지 여부 (기본값: False)
        include_hidden: 숨김 파일/폴더를 포함할지 여부 (기본값: False)
        
    Returns:
        파일 및 폴더 정보 목록 (경로, 유형, 심볼릭 링크 여부 등 포함)
        
    Raises:
        FileNotFoundError: 입력 경로가 존재하지 않는 경우
        PermissionError: 접근 권한이 없는 경우
    """
    root_path = Path(root_path)
    
    if not root_path.exists():
        raise FileNotFoundError(f"경로가 존재하지 않음: {root_path}")
    
    if not root_path.is_dir():
        raise ValueError(f"입력 경로가 디렉토리가 아님: {root_path}")
    
    try:
        items = []
        
        # 루트 디렉토리 자체를 항목으로 추가
        root_item = {
            'path': root_path,
            'rel_path': Path('.'),
            'is_dir': True,
            'is_symlink': root_path.is_symlink(),
            'is_hidden': is_hidden(root_path),
        }
        items.append(root_item)
        
        logger.info(f"디렉토리 스캔 시작: {root_path}")
        _scan_directory_recursive(
            root_path, 
            root_path, 
            items, 
            follow_symlinks, 
            include_hidden
        )
        logger.info(f"디렉토리 스캔 완료: {root_path}, 총 {len(items)}개 항목 발견")
        
        return items
    
    except PermissionError as e:
        logger.error(f"권한 오류: {e}")
        raise
    except Exception as e:
        logger.error(f"디렉토리 스캔 중 오류: {e}")
        raise

def _scan_directory_recursive(
    root_path: Path, 
    current_path: Path, 
    items: List[Dict[str, Any]], 
    follow_symlinks: bool, 
    include_hidden: bool
) -> None:
    """
    디렉토리를 재귀적으로 스캔하여 items 리스트에 추가
    
    Args:
        root_path: 스캔 시작 루트 경로
        current_path: 현재 스캔 중인 경로
        items: 결과를 추가할 리스트
        follow_symlinks: 심볼릭 링크를 따라갈지 여부
        include_hidden: 숨김 파일/폴더를 포함할지 여부
    """
    # 이미 처리된 경로 확인을 위한 집합
    processed_paths = {item['path'] for item in items}
    
    try:
        for path in current_path.iterdir():
            try:
                # 이미 처리된 경로는 건너뜀
                if path in processed_paths:
                    continue
                    
                is_symlink = path.is_symlink()
                is_dir = path.is_dir()
                is_hidden_item = is_hidden(path)
                
                # 숨김 항목이고 포함 설정이 꺼져있으면 건너뜀
                if is_hidden_item and not include_hidden:
                    continue
                
                # 심볼릭 링크이고 따라가지 않기로 설정했으면 링크 자체만 처리
                if is_symlink and not follow_symlinks:
                    is_dir = False  # 따라가지 않으므로 파일로 취급
                
                rel_path = path.relative_to(root_path)
                item = {
                    'path': path,
                    'rel_path': rel_path,
                    'is_dir': is_dir,
                    'is_symlink': is_symlink,
                    'is_hidden': is_hidden_item,
                }
                
                items.append(item)
                processed_paths.add(path)
                
                # 디렉토리이고 심볼릭 링크 설정에 따라 재귀 처리
                if is_dir and (not is_symlink or follow_symlinks):
                    _scan_directory_recursive(
                        root_path, 
                        path, 
                        items, 
                        follow_symlinks, 
                        include_hidden
                    )
            
            except PermissionError:
                logger.warning(f"접근 거부됨: {path}")
                items.append({
                    'path': path,
                    'rel_path': path.relative_to(root_path),
                    'is_dir': None,  # 알 수 없음
                    'is_symlink': path.is_symlink(),
                    'is_hidden': is_hidden(path),
                    'error': 'access_denied'
                })
                processed_paths.add(path)
            except Exception as e:
                logger.error(f"항목 처리 중 오류 ({path}): {e}")
    
    except PermissionError:
        logger.warning(f"디렉토리 접근 거부됨: {current_path}")
    except Exception as e:
        logger.error(f"디렉토리 스캔 중 오류 ({current_path}): {e}")

def is_hidden(path: Path) -> bool:
    """
    파일 또는 폴더가 숨김 항목인지 확인
    
    Args:
        path: 검사할 경로
        
    Returns:
        숨김 항목 여부
    """
    name = path.name
    
    # Unix/Linux/Mac 숨김 파일 (점으로 시작)
    if name.startswith('.'):
        return True
    
    # Windows 숨김 파일 속성
    if os.name == 'nt':
        try:
            import ctypes
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            return bool(attrs & 2)  # FILE_ATTRIBUTE_HIDDEN
        except (ImportError, AttributeError):
            # ctypes 모듈 없거나 Windows가 아닌 경우
            pass
    
    return False

def is_binary_file(file_path: Path) -> bool:
    """
    파일이 바이너리 파일인지 확인
    
    Args:
        file_path: 검사할 파일 경로
        
    Returns:
        바이너리 파일 여부
    """
    try:
        if not file_path.is_file():
            return False
            
        # 파일 크기가 0이면 텍스트 파일로 간주
        if file_path.stat().st_size == 0:
            return False
        
        # 일반적인 바이너리 파일 확장자 목록
        binary_extensions = {
            # 실행 파일 및 라이브러리
            '.exe', '.dll', '.so', '.dylib', '.bin', '.o', '.obj',
            # 압축 파일
            '.zip', '.gz', '.tar', '.rar', '.7z', '.xz', '.bz2',
            # 이미지 파일
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.ico', '.webp',
            # 오디오 파일
            '.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma',
            # 비디오 파일
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
            # 문서 및 기타 바이너리 파일
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.class', '.pyc', '.pyd', '.pyo', '.db', '.sqlite', '.mdb',
            # 기타 바이너리 형식
            '.ttf', '.woff', '.woff2', '.eot', '.otf'
        }
        
        # 확장자로 빠르게 확인
        if file_path.suffix.lower() in binary_extensions:
            return True
            
        # 파일 앞부분을 읽어 바이너리 여부 확인
        chunk_size = min(1024, file_path.stat().st_size)
        with open(file_path, 'rb') as f:
            chunk = f.read(chunk_size)
            
        # 널 바이트가 포함되어 있으면 바이너리 파일로 간주
        return b'\x00' in chunk
            
    except Exception as e:
        logger.error(f"파일 타입 확인 중 오류 ({file_path}): {e}")
        return False  # 오류 발생 시 기본적으로 바이너리가 아닌 것으로 가정

def read_text_file(file_path: Path) -> Optional[Union[str, Dict[str, Any]]]:
    """
    텍스트 파일 내용을 읽어 문자열로 반환
    
    Args:
        file_path: 읽을 파일 경로
        
    Returns:
        성공 시: 파일 내용 문자열
        실패 시: None 또는 오류 정보가 포함된 딕셔너리
            {'error': str, 'error_type': str, 'details': str}
    """
    try:
        # 파일이 존재하지 않는 경우 오류 정보 반환
        if not file_path.exists():
            return {
                'error': 'file_not_found',
                'error_type': 'FileNotFoundError',
                'details': f"파일이 존재하지 않음: {file_path}"
            }
            
        # 바이너리 파일인 경우 오류 정보 반환
        if is_binary_file(file_path):
            logger.debug(f"바이너리 파일 읽기 건너뜀: {file_path}")
            return {
                'error': 'binary_file',
                'error_type': 'TypeError',
                'details': f"바이너리 파일은 텍스트로 읽을 수 없음: {file_path}"
            }
            
        # 확장된 인코딩 목록
        encodings = [
            'utf-8', 'utf-8-sig',  # BOM 포함된 UTF-8
            'utf-16', 'utf-16-le', 'utf-16-be',
            'latin-1', 'iso-8859-1',
            'cp1252',  # Windows 서유럽
            'euc-kr', 'cp949',  # 한국어
            'shift-jis', 'cp932',  # 일본어
            'gb2312', 'gbk', 'gb18030',  # 중국어
            'cp1251',  # 키릴 문자
            'ascii'  # 마지막 시도
        ]

        # 첫 번째로 UTF-8 시도
        try:
            content = file_path.read_text(encoding='utf-8')
            return content
        except UnicodeDecodeError:
            pass  # 다른 인코딩 시도
            
        # 다른 인코딩 시도
        decode_errors = []
        for encoding in encodings[1:]:  # UTF-8은 이미 시도했으므로 건너뜀
            try:
                content = file_path.read_text(encoding=encoding)
                logger.debug(f"파일 성공적으로 읽음 (인코딩: {encoding}): {file_path}")
                return content
            except UnicodeDecodeError as e:
                decode_errors.append(f"{encoding}: {str(e)}")
                continue
                
        # 모든 인코딩 실패 시
        logger.warning(f"파일 인코딩 감지 실패: {file_path}")
        return {
            'error': 'encoding_detection_failed',
            'error_type': 'UnicodeDecodeError',
            'details': f"지원하는 모든 인코딩으로 파일을 읽을 수 없음: {file_path}",
            'attempted_encodings': encodings,
            'decode_errors': decode_errors[:3]  # 처음 3개 오류만 포함
        }
            
    except PermissionError:
        logger.warning(f"파일 읽기 권한 없음: {file_path}")
        return {
            'error': 'access_denied',
            'error_type': 'PermissionError',
            'details': f"파일 읽기 권한이 없음: {file_path}"
        }
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"파일 읽기 오류 ({file_path}): {e}")
        return {
            'error': 'read_error',
            'error_type': error_type,
            'details': f"파일 읽기 중 오류 발생: {str(e)}"
        } 