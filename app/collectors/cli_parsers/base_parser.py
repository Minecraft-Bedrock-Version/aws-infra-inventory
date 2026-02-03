"""
기본 파서 추상 클래스

모든 서비스별 CLI 파서는 이 클래스를 상속받아야 합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import re
from datetime import datetime, timezone


class BaseParser(ABC):
    """
    AWS CLI 명령어 파서를 위한 기본 틀(추상 클래스)입니다.
    
    모든 서비스 파서는 다음을 반드시 구현해야 합니다:
    1. service_name: 서비스 이름 (예: "iam", "ec2")
    2. supported_commands: 지원하는 명령어 리스트
    3. parse_command: 명령어 파싱 함수
    """
    
    @property
    @abstractmethod
    def service_name(self) -> str:
        """
        서비스 식별자(이름)를 반환합니다.
        파서 레지스트리가 이 이름을 보고 요청을 연결해줍니다.
        
        Returns:
            str: 서비스 이름 (예: "iam", "ec2", "s3")
        """
        pass
    
    @property
    @abstractmethod
    def supported_commands(self) -> List[str]:
        """
        이 파서가 지원하는 CLI 명령어 리스트를 반환합니다.
        
        Returns:
            List[str]: 명령어 패턴 리스트
            예: ["create-user", "put-user-policy", "attach-user-policy"]
        """
        pass
    
    @abstractmethod
    def parse_command(self, cli_text: str, account_id: str, **kwargs) -> Dict[str, Any]:
        """
        CLI 명령어를 파싱하여 표준 노드/엣지 포맷으로 변환합니다.
        
        Args:
            cli_text: AWS CLI 명령어 문자열 (여러 줄 가능)
            account_id: AWS 계정 ID
            **kwargs: 추가 컨텍스트 정보
        
        Returns:
            Dict containing:
            {
                "schema_version": "1.0",
                "collected_at": "<timestamp>",
                "account_id": "<account_id>",
                "nodes": [...],
                "edges": []
            }
        """
        pass
    
    # ===== 공통 유틸리티 메서드 (모든 파서가 사용) =====
    
    @staticmethod
    def _iso_now() -> str:
        """현재 시각을 ISO 8601 포맷으로 반환"""
        return datetime.now(timezone.utc).isoformat()
    
    @staticmethod
    def _collapse_cli(cli_text: str) -> str:
        """
        줄바꿈 + 백슬래시(\)로 이어진 CLI를 한 줄로 정리
        불필요한 공백을 정리
        """
        # backslash newline 제거
        s = re.sub(r"\\\s*\n", " ", cli_text)
        # 나머지 줄바꿈을 공백으로
        s = re.sub(r"\s*\n\s*", " ", s)
        # 연속 공백 정리
        s = re.sub(r"\s+", " ", s).strip()
        return s
    
    @staticmethod
    def _extract_flag_value(cli_line: str, flag: str) -> str:
        """
        --flag value 형태를 찾는다.
        value가 따옴표로 감싸졌든 아니든 처리.
        """
        # 1) 따옴표로 감싼 값: --flag '...'
        m = re.search(rf"{re.escape(flag)}\s+'([^']*)'", cli_line)
        if m:
            return m.group(1)
        
        # 2) 따옴표로 감싼 값: --flag "..."
        m = re.search(rf'{re.escape(flag)}\s+"([^"]*)"', cli_line)
        if m:
            return m.group(1)
        
        # 3) 일반 토큰 값: --flag token
        m = re.search(rf"{re.escape(flag)}\s+([^\s]+)", cli_line)
        if m:
            return m.group(1)
        
        return None