import json
from typing import Any, Dict, List

def transform_lambda_to_graph(normalized_data: Any) -> Dict[str, Any]:
    # 1. [방어 로직] 데이터가 문자열(str)로 들어올 경우를 대비한 역직렬화
    curr = normalized_data
    try:
        for _ in range(3): # 최대 3번까지 중첩 JSON 해제 시도
            if isinstance(curr, (str, bytes)):
                curr = json.loads(curr)
            else:
                break
    except Exception:
        return {"nodes": [], "edges": []}

    if not isinstance(curr, dict):
        return {"nodes": [], "edges": []}

    # 2. [구조 보정] RDS와 마찬가지로 {'nodes': {'nodes': [...]}} 구조 대응
    outer_nodes = curr.get("nodes", {})
    if isinstance(outer_nodes, dict):
        nodes_payload = outer_nodes.get("nodes", [])
        account_id = outer_nodes.get("account_id", curr.get("account_id", "unknown"))
        collected_at = outer_nodes.get("collected_at", curr.get("collected_at"))
    else:
        # 바로 리스트가 들어있는 경우
        nodes_payload = outer_nodes if isinstance(outer_nodes, list) else []
        account_id = curr.get("account_id", "unknown")
        collected_at = curr.get("collected_at")

    graph_data = {
        "schema_version": "1.0",
        "collected_at": collected_at,
        "account_id": account_id,
        "nodes": [],
        "edges": []
    }

    # 3. 노드 처리 루프
    for node in nodes_payload:
        if not isinstance(node, dict): continue
        
        # 타입 체크 시 대소문자 방어
        node_type = str(node.get("node_type", "")).lower()
        n_id = node.get("node_id")
        res_id = node.get("resource_id")
        region = node.get("region", "us-east-1")
        attrs = node.get("attributes", {})
        rels = node.get("relationships", {})
        name = node.get("name") or res_id
        
        # 3-1. Lambda Function 노드 (타입명 유연하게 체크)
        if "function" in node_type or node_type == "lambda":
            # [Linker 핵심] VPC 연결을 위한 SubnetId 추출
            vpc_config = attrs.get("vpc_config", {})
            subnet_ids = vpc_config.get("SubnetIds", []) if isinstance(vpc_config, dict) else []
            
            # [Linker 핵심] IAM 연결을 위한 Role 정보
            # relationships에 있거나 attributes의 'role' 필드 확인
            role_arn = rels.get("role_arn") or attrs.get("role")

            new_node = {
                "id": n_id,
                "type": "lambda",
                "name": name,
                "arn": attrs.get("arn") or rels.get("function_arn"),
                "region": region,
                "properties": {
                    "runtime": attrs.get("runtime"),
                    "handler": attrs.get("handler"),
                    "role_arn": role_arn, # Linker가 IAM Role 노드와 연결할 때 사용
                    "subnets": subnet_ids, # Linker가 Subnet 노드와 연결할 때 사용
                    "timeout": attrs.get("timeout"),
                    "memory_size": attrs.get("memory_size"),
                    "vpc_id": vpc_config.get("VpcId") if isinstance(vpc_config, dict) else None
                }
            }
            graph_data["nodes"].append(new_node)

            # 4-1. MEMBER_OF 엣지 (Lambda -> VPC) 직접 생성 (Linker 보조)
            vpc_id = vpc_config.get("VpcId") if isinstance(vpc_config, dict) else None
            if vpc_id:
                graph_data["edges"].append({
                    "id": f"edge:{res_id}:MEMBER_OF:{vpc_id}",
                    "relation": "MEMBER_OF",
                    "src": n_id,
                    "dst": f"{account_id}:{region}:vpc:{vpc_id}",
                    "directed": True
                })

        # 3-2. Event Source Mapping (예: SQS 연동)
        elif "mapping" in node_type:
            graph_data["nodes"].append({
                "id": n_id,
                "type": "lambda_event_source_mapping",
                "name": name,
                "properties": {
                    "state": attrs.get("state"),
                    "function_arn": attrs.get("function_arn")
                }
            })

    return graph_data