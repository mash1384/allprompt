from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, Signal, QThread

from src.core.tokenizer import Tokenizer
from src.core.file_scanner import is_binary_file, read_text_file
import logging

logger = logging.getLogger(__name__)

class TokenizerThread(QThread):
    """
    백그라운드 토큰 계산 스레드
    """
    # 시그널 정의
    progress_updated = Signal(int, int)  # 현재 진행 상태, 총 파일 수
    token_calculated = Signal(str, int)  # 파일 경로, 토큰 수
    calculation_finished = Signal()      # 계산 완료 시그널
    calculation_error = Signal(str)      # 오류 발생 시 메시지
    
    def __init__(self, files: List[Path], tokenizer: Tokenizer):
        """
        토큰화 스레드 초기화
        
        Args:
            files: 토큰 수를 계산할 파일 경로 목록
            tokenizer: 토큰화 객체
        """
        super().__init__()
        self.files = files
        self.tokenizer = tokenizer
        self.stopped = False
    
    def stop(self):
        """스레드 중지 요청"""
        self.stopped = True
    
    def run(self):
        """
        백그라운드에서 파일 목록의 토큰 수를 계산
        """
        try:
            total_files = len(self.files)
            for i, file_path in enumerate(self.files):
                # 종료 요청 확인
                if self.stopped:
                    break
                
                # 진행 상황 업데이트
                self.progress_updated.emit(i + 1, total_files)
                
                # 바이너리 파일은 건너뜀
                if is_binary_file(file_path):
                    self.token_calculated.emit(str(file_path), 0)
                    continue
                
                # 파일 내용 읽기
                content = read_text_file(file_path)
                
                # 오류 정보가 포함된 딕셔너리인 경우 건너뜀
                if isinstance(content, dict) and 'error' in content:
                    self.token_calculated.emit(str(file_path), 0)
                    continue
                
                # 토큰 수 계산
                token_count = self.tokenizer.count_tokens(content)
                
                # 결과 전송
                self.token_calculated.emit(str(file_path), token_count)
            
            # 계산 완료
            self.calculation_finished.emit()
        except Exception as e:
            logger.error(f"토큰 계산 중 오류: {e}")
            self.calculation_error.emit(str(e))

class TokenController(QObject):
    """
    토큰 계산 로직을 관리하는 컨트롤러
    """
    # 시그널 정의
    token_progress_signal = Signal(int, int)  # current, total
    total_tokens_updated_signal = Signal(str, int)  # formatted token count, files count
    token_calculation_status_signal = Signal(str, bool)  # message, is_error
    
    def __init__(self, parent=None):
        """
        TokenController 초기화
        """
        super().__init__(parent)
        self.tokenizer = Tokenizer()  # Default tokenizer
        self.token_cache = {}  # Cache for token counts {file_path: token_count}
        self.total_tokens = 0  # Total token count for selected files
        self.token_thread = None  # Background calculation thread
    
    def calculate_tokens(self, checked_items_set: set, files_count: int = None):
        """
        체크된 항목의 토큰 수를 계산합니다.
        
        Args:
            checked_items_set: 체크된 항목 경로 Set
            files_count: 체크된 파일 수 (None이면 자동 계산)
        """
        # 파일 목록만 필터링
        files_to_calculate = [Path(path) for path in checked_items_set if Path(path).is_file()]
        
        # files_count가 제공되지 않으면 직접 계산
        if files_count is None:
            files_count = len(files_to_calculate)
        
        if files_to_calculate:
            self.start_calculation(files_to_calculate, files_count)
        else:
            # 파일이 없으면 토큰 수 업데이트만 진행
            self._update_token_count(checked_paths=None, files_count=files_count)
    
    def start_calculation(self, files: List[Path], files_count: int = None):
        """
        지정된 파일 목록의 토큰 수 계산 시작
        
        Args:
            files: 토큰 수를 계산할 파일 목록
            files_count: 체크된 파일 수 (None이면 자동 계산)
        """
        self._start_token_calculation(files, files_count)
    
    def _start_token_calculation(self, files: List[Path], files_count: int = None):
        """
        지정된 파일 목록의 토큰 수 계산 시작 (내부 메소드)
        
        Args:
            files: 토큰 수를 계산할 파일 목록
            files_count: 체크된 파일 수 (None이면 자동 계산)
        """
        # 이미 실행 중인 스레드가 있으면 중지
        if self.token_thread and self.token_thread.isRunning():
            self.token_thread.stop()
            self.token_thread.wait()
        
        # files_count가 제공되지 않으면 직접 계산
        if files_count is None:
            files_count = len(files)
        
        if not files:
            # 파일이 없으면 토큰 수 업데이트만 진행
            self._update_token_count(files_count=files_count)
            return
        
        # 클래스 변수에 파일 수 저장 (완료 시 사용)
        self.current_files_count = files_count
        
        # 계산 시작 메시지
        self.token_calculation_status_signal.emit("토큰 계산을 시작합니다...", False)
        
        # 스레드 생성 및 시작
        self.token_thread = TokenizerThread(files, self.tokenizer)
        
        # 시그널 연결
        self.token_thread.progress_updated.connect(self._on_token_progress)
        self.token_thread.token_calculated.connect(self._on_token_calculated)
        self.token_thread.calculation_finished.connect(self._on_token_calculation_finished)
        self.token_thread.calculation_error.connect(self._on_token_calculation_error)
        
        # 스레드 시작
        self.token_thread.start()
    
    def _on_token_progress(self, current: int, total: int):
        """
        토큰 계산 진행 상황 처리
        
        Args:
            current: 현재 처리 중인 파일 인덱스
            total: 전체 파일 수
        """
        # 진행 상황 시그널 발생
        self.token_progress_signal.emit(current, total)
        
        # 상태 메시지 업데이트
        status_msg = f"토큰 계산 중... ({current}/{total})"
        self.token_calculation_status_signal.emit(status_msg, False)
    
    def _on_token_calculated(self, file_path: str, token_count: int):
        """
        개별 파일의 토큰 계산 완료 처리
        
        Args:
            file_path: 계산이 완료된 파일 경로
            token_count: 계산된 토큰 수
        """
        # 토큰 수 캐시 업데이트
        self.token_cache[file_path] = token_count
    
    def _on_token_calculation_finished(self):
        """토큰 계산 완료 처리"""
        # 상태 메시지 업데이트
        self.token_calculation_status_signal.emit("토큰 계산 완료", False)
        
        # 토큰 수 업데이트 (UI 갱신)
        self._update_token_count(files_count=getattr(self, 'current_files_count', None))
        
        # 로그 기록
        logger.debug(f"Token calculation finished: {len(self.token_cache)} files calculated")
    
    def _on_token_calculation_error(self, error_msg: str):
        """
        토큰 계산 중 오류 처리
        
        Args:
            error_msg: 오류 메시지
        """
        # 오류 메시지 업데이트
        self.token_calculation_status_signal.emit(f"토큰 계산 중 오류: {error_msg}", True)
        
        # 로그 기록
        logger.error(f"Token calculation error: {error_msg}")
    
    def _update_token_count(self, checked_paths=None, files_count=None):
        """
        선택된 파일들의 총 토큰 수 업데이트
        
        Args:
            checked_paths: 선택된 파일/폴더 경로 목록 (None인 경우 MainWindow에서 가져옴)
            files_count: 선택된 파일 수 (None인 경우 자동 계산)
        """
        # 토큰 수 초기화
        self.total_tokens = 0
        
        # 파일 수 기본값
        if files_count is None:
            files_count = 0
        
        # 선택된 경로가 제공된 경우에만 계산
        if checked_paths:
            # 파일 수 계산 필요한 경우
            file_paths = []
            
            for path in checked_paths:
                path_str = str(path)
                # 파일이고 캐시에 있으면 토큰 수 추가
                if path.is_file():
                    file_paths.append(path)
                    if path_str in self.token_cache:
                        self.total_tokens += self.token_cache[path_str]
            
            # 파일 수가 제공되지 않았으면 계산
            if files_count is None:
                files_count = len(file_paths)
        
        # 토큰 수 포맷팅 및 시그널 발생
        formatted_tokens = f"{self.total_tokens:,}"
        self.total_tokens_updated_signal.emit(formatted_tokens, files_count)
        
        return formatted_tokens
    
    def clear_cache(self):
        """토큰 캐시 초기화"""
        self.token_cache.clear()
        self.total_tokens = 0 