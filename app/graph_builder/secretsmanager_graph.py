from __future__ import annotations
from typing import Any, Dict

def graph_secrets_manager(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    secrets = raw_payload.get("secretsmanager", {}).get("secrets", [])
    rds_instances = raw_payload.get("rds", {}).get("instances", [])
    lambda_functions = raw_payload.get("lambda", {}).get("functions", [])
    
    edges = []
    seen_edges = set()

    def _add_edge(edge_id: str, relation: str, src: str, dst: str, conditions: str) -> None:
        if edge_id in seen_edges:
            return
        seen_edges.add(edge_id)
        edges.append({
            "id": edge_id,
            "relation": relation,
            "src": src,
            "dst": dst,
            "directed": True,
            "conditions": conditions,
        })

    for secret_value in secrets: # 시크릿 목록 순회
        node_type = "secretsmanager"
        name = secret_value.get("Name")
        node_id = f"{account_id}:{region}:{node_type}:{name}"

        # (1) Secrets Manager가 RDS 자격 증명을 관리함 (SECRETS_MANAGE_RDS)
        # - 시크릿 이름이나 내용에 RDS 식별자가 포함된 경우 연결
        secret_string = secret_value.get("SecretString", "") # 시크릿 값 불러오기
        for rds in rds_instances: # RDS 인스턴스 목록 순회
            rds_id = rds.get("DBInstanceIdentifier")
            endpoint = rds.get("Endpoint", {}).get("Address")
            rds_node_id = f"{account_id}:{region}:rds:{rds_id}"
            
            # 시크릿 명칭에 RDS ID가 있거나, 시크릿 내용에 엔드포인트가 포함된 경우
            if (rds_id in name) or (secret_string and (rds_id in secret_string or (endpoint and endpoint in secret_string))):
                edge_id = f"edge:{name}:SECRETS_MANAGE_RDS:{rds_id}"
                
                if edge_id not in seen_edges:
                    seen_edges.add(edge_id)
                    edges.append({
                        "id": edge_id,
                        "relation": "SECRETS_MANAGE_RDS",
                        "src": node_id,
                        "dst": rds_node_id,
                        "directed": True,
                        "conditions": "This secret contains or is named after credentials for the associated RDS instance."
                    })

        # (2) Lambda 함수가 환경 변수에서 시크릿을 참조함 (LAMBDA_REFERENCE_SECRET)
        for func in lambda_functions: # 람다 함수 목록 순회
            fname = func.get("FunctionName")
            f_node_id = f"{account_id}:{region}:lambda:{fname}"
            env_vars = func.get("Environment", {}).get("Variables", {}) # 환경 변수 불러오기
            
            for key, val in env_vars.items(): # 환경 변수 키/값 순회
                if name in str(val): # 환경 변수 값에 시크릿 이름이나 ARN이 포함된 경우
                    edge_id = f"edge:{fname}:LAMBDA_REFERENCE_SECRET:{name}"
                    
                    if edge_id not in seen_edges:
                        seen_edges.add(edge_id)
                        edges.append({
                            "id": edge_id,
                            "relation": "LAMBDA_REFERENCE_SECRET",
                            "src": f_node_id,
                            "dst": node_id,
                            "directed": True,
                            "conditions": f"Lambda refers to secret '{name}' in environment variable '{key}'."
                        })

        # (3) 시크릿 리소스 정책이 특정 IAM 주체에게 접근을 허용함 (RESOURCE_POLICY_ALLOW)
        policy = secret_value.get("ResourcePolicy") # 리소스 기반 정책 불러오기
        if policy and isinstance(policy, dict): # 정책이 존재하고 딕셔너리 형태일 때만 분석
            for stmt in policy.get("Statement", []):
                if stmt.get("Effect") == "Allow": # Allow 정책인 경우
                    principal = stmt.get("Principal", {})
                    aws_p = principal.get("AWS")
                    if aws_p:
                        if isinstance(aws_p, str): aws_p = [aws_p] # 문자열이면 리스트로 변환
                        for p in aws_p: # Principal 목록 순회
                            p_name = p.split("/")[-1] # Principal 이름 추출
                            src_node = f"{account_id}:iam_resource:{p_name}"
                            edge_id = f"edge:{p_name}:RESOURCE_POLICY_ALLOW:{name}"
                            
                            if edge_id not in seen_edges:
                                seen_edges.add(edge_id)
                                edges.append({
                                    "id": edge_id,
                                    "relation": "RESOURCE_POLICY_ALLOW",
                                    "src": src_node,
                                    "dst": node_id,
                                    "directed": True,
                                    "conditions": "Resource-based policy explicitly allows this principal to access the secret."
                                })

    return edges
