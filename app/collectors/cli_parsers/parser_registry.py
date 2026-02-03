"""
파서 레지스트리 (자동 검색 시스템)

작성된 파서들을 자동으로 찾아서 등록해주는 관리자입니다.
새로운 파서 파일(예: ec2_parser.py)만 만들면 알아서 인식합니다.
"""

import importlib
import inspect
import re
from pathlib import Path
from typing import Dict, Optional
from .base_parser import BaseParser


class ParserRegistry:
    """
    CLI 파서 저장소입니다.
    현재 폴더에 있는 모든 *_parser.py 파일을 찾아서 자동으로 등록합니다.
    """
    
    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}
        self._command_to_service: Dict[str, str] = {}  # 명령어 -> 서비스 매핑
        self._discover_parsers()
    
    def _discover_parsers(self):
        """
        현재 디렉토리를 스캔하여 자동으로 파서를 찾아 등록합니다.
        """
        # 현재 파일이 있는 디렉토리
        current_dir = Path(__file__).parent
        
        # 현재 디렉토리의 모든 .py 파일 탐색
        for file_path in current_dir.glob("*_parser.py"):
            # base_parser.py는 추상 클래스이므로 제외
            if file_path.name == "base_parser.py":
                continue
            
            # 모듈 이름 (확장자 제외)
            module_name = file_path.stem
            
            try:
                # 모듈 동적 임포트 (예: from . import iam_parser)
                module = importlib.import_module(f".{module_name}", package="collectors.cli_parsers")
                
                # 모듈 내의 모든 클래스 검사
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # BaseParser를 상속받았는지 확인 (BaseParser 자체는 제외)
                    if (issubclass(obj, BaseParser) and 
                        obj is not BaseParser and
                        hasattr(obj, 'service_name')):
                        
                        # 파서 인스턴스(객체) 생성 및 등록
                        parser_instance = obj()
                        service_name = parser_instance.service_name
                        self._parsers[service_name] = parser_instance
                        
                        # 명령어별 매핑도 등록
                        for cmd in parser_instance.supported_commands:
                            self._command_to_service[cmd] = service_name
                        
                        print(f"[OK] 파서 등록 완료: {service_name} ({name}) - {len(parser_instance.supported_commands)} commands")
                        
            except Exception as e:
                print(f"[WARNING] 파서 로딩 실패 ({module_name}): {e}")
    
    def detect_service(self, cli_text: str) -> str:
        """
        CLI 텍스트에서 서비스 타입을 자동 감지합니다.
        
        Args:
            cli_text: AWS CLI 명령어 문자열
            
        Returns:
            str: 서비스 이름 (예: "iam", "ec2")
            
        Raises:
            ValueError: 알 수 없는 명령어인 경우
        """
        normalized = BaseParser._collapse_cli(cli_text).lower()
        
        # aws <service> <command> 패턴에서 추출
        # 예: "aws iam create-user" -> service="iam", command="create-user"
        match = re.match(r'aws\s+(\w+)\s+([a-z-]+)', normalized)
        if not match:
            raise ValueError(f"Invalid CLI format: {cli_text[:100]}...")
        
        service = match.group(1)
        command = match.group(2)
        
        # 서비스가 등록되어 있는지 확인
        if service not in self._parsers:
            available = list(self._parsers.keys())
            raise ValueError(
                f"Unsupported service: '{service}'. "
                f"Available services: {available}"
            )
        
        # 해당 파서가 이 명령어를 지원하는지 확인
        parser = self._parsers[service]
        if command not in parser.supported_commands:
            raise ValueError(
                f"Service '{service}' does not support command '{command}'. "
                f"Supported commands: {parser.supported_commands}"
            )
        
        return service
    
    def get_parser(self, service: str) -> BaseParser:
        """
        서비스 이름에 맞는 파서를 찾아줍니다.
        
        Args:
            service: 서비스 이름 (예: "iam", "ec2", "s3")
        
        Returns:
            BaseParser: 해당 서비스의 파서
        
        Raises:
            ValueError: 등록되지 않은 서비스를 요청했을 때
        """
        if service not in self._parsers:
            available = ", ".join(self._parsers.keys())
            raise ValueError(
                f"'{service}' 서비스를 처리할 파서가 없습니다. "
                f"현재 가능한 서비스: {available}"
            )
        
        return self._parsers[service]
    
    def parse(self, cli_text: str, account_id: str, **kwargs) -> Dict:
        """
        CLI 명령어를 자동으로 감지하고 파싱합니다.
        
        Args:
            cli_text: AWS CLI 명령어 문자열
            account_id: AWS 계정 ID
            **kwargs: 추가 파라미터
            
        Returns:
            dict: 파싱된 노드/엣지 데이터
        """
        if not cli_text or not cli_text.strip():
            return {
                "schema_version": "1.0",
                "collected_at": BaseParser._iso_now(),
                "account_id": account_id,
                "nodes": [],
                "edges": []
            }
        
        # 서비스 자동 감지
        service = self.detect_service(cli_text)
        
        # 해당 파서로 위임
        parser = self.get_parser(service)
        return parser.parse_command(cli_text, account_id, **kwargs)
    
    def list_services(self) -> list:
        """현재 등록된 모든 서비스 목록을 반환합니다."""
        return list(self._parsers.keys())


# 전역 레지스트리 인스턴스 (싱글톤 패턴)
# 프로그램 실행 시 한 번만 만들어져서 계속 사용됩니다.
_registry = ParserRegistry()


def parse_cli(cli_text: str, account_id: str, **kwargs) -> Dict:
    """
    외부에서 CLI를 파싱하기 위한 헬퍼 함수입니다.
    
    Args:
        cli_text: AWS CLI 명령어 문자열
        account_id: AWS 계정 ID
    
    Returns:
        dict: 파싱된 노드/엣지 데이터
    """
    return _registry.parse(cli_text, account_id, **kwargs)


def get_parser(service: str) -> BaseParser:
    """
    외부에서 특정 서비스 파서를 가져오기 위한 헬퍼 함수입니다.
    
    Args:
        service: 서비스 이름 (예: "iam")
    
    Returns:
        BaseParser: 해당 서비스의 파서 인스턴스
    """
    return _registry.get_parser(service)


def list_supported_services() -> list:
    """
    외부에서 가능한 서비스 목록을 쉽게 보기 위한 헬퍼 함수입니다.
    
    Returns:
        list: 지원되는 서비스 이름 리스트
    """
    return _registry.list_services()