"""
CLI 수집 핸들러

CLI 명령어를 파싱하여 노드/엣지로 변환합니다.
새로운 파서 레지스트리 시스템을 사용합니다.
"""

from collectors.cli_parsers import parse_cli


def run_cli_collector(cli_input: str, account_id: str) -> dict:
    """
    CLI 명령어를 파싱하여 노드/엣지로 변환
    
    Args:
        cli_input: AWS CLI 명령어 문자열 (여러 줄 가능)
        account_id: AWS 계정 ID
        
    Returns:
        dict: 파싱된 노드/엣지 데이터
              {"nodes": [...], "edges": []}
    """
    if not cli_input or cli_input.strip() == "":
        return {"nodes": [], "edges": []}
    
    try:
        # 새로운 파서 레지스트리 사용 (자동 서비스 감지)
        result = parse_cli(cli_input, account_id)
        return result
        
    except Exception as e:
        print(f"CLI 파싱 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return {"nodes": [], "edges": []}