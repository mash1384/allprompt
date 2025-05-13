#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
토큰화 모듈
텍스트를 LLM 모델 기준의 토큰으로 변환하고 토큰 수를 계산합니다.
"""

import logging
from typing import Optional, Dict, List, Union, Any
import tiktoken

logger = logging.getLogger(__name__)

# 토큰화 모델 매핑
# 모델명: (인코딩 이름, 최대 토큰 수)
TOKENIZER_MODELS = {
    "gpt-3.5-turbo": ("cl100k_base", 4096),
    "gpt-3.5-turbo-16k": ("cl100k_base", 16384),
    "gpt-4": ("cl100k_base", 8192),
    "gpt-4-32k": ("cl100k_base", 32768),
    "gpt-4-turbo": ("cl100k_base", 128000),
    "text-embedding-ada-002": ("cl100k_base", None),
}

class Tokenizer:
    """LLM 텍스트 토큰화 클래스"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        """
        토큰화 객체 초기화
        
        Args:
            model_name: 토큰화에 사용할 모델 이름 (기본값: "gpt-3.5-turbo")
            
        Raises:
            ValueError: 지원하지 않는 모델명이 제공된 경우
        """
        self.model_name = model_name
        
        if model_name not in TOKENIZER_MODELS:
            logger.warning(f"지원하지 않는 모델: {model_name}, 기본 모델로 대체합니다.")
            self.model_name = "gpt-3.5-turbo"
            
        encoding_name, _ = TOKENIZER_MODELS[self.model_name]
        
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
            logger.info(f"토큰화 모델 초기화: {model_name} (인코딩: {encoding_name})")
        except Exception as e:
            logger.error(f"토큰화 인코딩 초기화 실패: {e}")
            raise
    
    def count_tokens(self, text: Optional[str]) -> int:
        """
        텍스트의 토큰 수 계산
        
        Args:
            text: 토큰 수를 계산할 텍스트
            
        Returns:
            토큰 수 (텍스트가 None이거나 빈 문자열이면 0 반환)
        """
        if text is None or text == "":
            return 0
            
        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.error(f"토큰 수 계산 중 오류: {e}")
            return 0
            
    def get_available_models(self) -> List[str]:
        """
        사용 가능한 토큰화 모델 목록 반환
        
        Returns:
            모델 이름 목록
        """
        return list(TOKENIZER_MODELS.keys())
        
    def get_model_max_tokens(self, model_name: Optional[str] = None) -> Optional[int]:
        """
        지정된 모델의 최대 토큰 수 반환
        
        Args:
            model_name: 조회할 모델 이름 (기본값: 현재 설정된 모델)
            
        Returns:
            최대 토큰 수 또는 제한이 없는 경우 None
        """
        if model_name is None:
            model_name = self.model_name
            
        if model_name not in TOKENIZER_MODELS:
            return None
            
        _, max_tokens = TOKENIZER_MODELS[model_name]
        return max_tokens 