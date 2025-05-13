#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
필터링 모듈
.gitignore 파일을 파싱하고 파일/폴더 경로에 필터 규칙을 적용합니다.
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Union, Tuple
import pathspec

logger = logging.getLogger(__name__)

class GitignoreFilter:
    """GitIgnore 기반 파일 필터링 클래스"""
    
    def __init__(self, root_dir: Union[str, Path]):
        """
        GitIgnore 필터 초기화
        
        Args:
            root_dir: .gitignore 파일을 찾을 루트 디렉토리
        """
        self.root_dir = Path(root_dir)
        self.spec = None
        self.gitignore_path = None
        
        # .gitignore 파일 찾기 및 로드
        self._load_gitignore()
    
    def _load_gitignore(self) -> None:
        """
        루트 디렉토리에서 .gitignore 파일을 찾아 로드
        
        찾지 못하면 self.spec은 None으로 유지됨
        """
        gitignore_path = self.root_dir / '.gitignore'
        
        if not gitignore_path.exists() or not gitignore_path.is_file():
            logger.info(f".gitignore 파일을 찾을 수 없음: {gitignore_path}")
            return
        
        try:
            self.gitignore_path = gitignore_path
            
            # .gitignore 파일 읽기
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                gitignore_content = f.read()
            
            # pathspec 객체 생성
            self.spec = pathspec.PathSpec.from_lines(
                pathspec.patterns.GitWildMatchPattern, 
                gitignore_content.splitlines()
            )
            
            logger.info(f".gitignore 파일 로드 완료: {gitignore_path}")
        except Exception as e:
            logger.error(f".gitignore 파일 로드 중 오류: {e}")
            self.spec = None
    
    def should_ignore(self, path: Union[str, Path]) -> bool:
        """
        지정한 경로가 .gitignore 규칙에 의해 무시되어야 하는지 확인
        
        Args:
            path: 확인할 경로 (절대 경로 또는 상대 경로)
            
        Returns:
            무시해야 하면 True, 아니면 False
        """
        if self.spec is None:
            return False
        
        try:
            # 절대 경로를 루트 디렉토리 기준 상대 경로로 변환
            path = Path(path)
            if path.is_absolute():
                try:
                    rel_path = path.relative_to(self.root_dir)
                    path_str = str(rel_path)
                except ValueError:
                    # 루트 디렉토리의 하위 경로가 아니면 무시하지 않음
                    return False
            else:
                path_str = str(path)
            
            # 경로 구분자 변환 (OS 독립적 처리)
            path_str = path_str.replace(os.sep, '/')
            
            # pathspec으로 경로 매치 확인
            return self.spec.match_file(path_str)
        except Exception as e:
            logger.error(f"경로 필터링 중 오류 ({path}): {e}")
            return False
    
    def has_gitignore(self) -> bool:
        """
        유효한 .gitignore 파일이 로드되었는지 확인
        
        Returns:
            .gitignore 파일이 로드되었으면 True, 아니면 False
        """
        return self.spec is not None
    
    def get_gitignore_path(self) -> Optional[Path]:
        """
        로드된 .gitignore 파일 경로 반환
        
        Returns:
            .gitignore 파일 경로 또는 None (로드되지 않은 경우)
        """
        return self.gitignore_path
        
    def filter_paths(self, paths: List[Union[str, Path]]) -> List[Union[str, Path]]:
        """
        경로 목록에서 .gitignore 규칙에 의해 무시되어야 하는 항목 제외
        
        Args:
            paths: 경로 목록
            
        Returns:
            필터링된 경로 목록
        """
        if self.spec is None:
            return paths
            
        try:
            return [path for path in paths if not self.should_ignore(path)]
        except Exception as e:
            logger.error(f"경로 목록 필터링 중 오류: {e}")
            return paths 