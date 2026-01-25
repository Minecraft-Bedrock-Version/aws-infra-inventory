import json
from typing import Any, Dict, List

def transform_rds_to_graph(rds_normalized_data: Any) -> Dict[str, Any]:
    # 1. 타입 확인 및 전처리
    if not isinstance(rds_normalized_data, dict):
        return {"nodes": [], "edges": []}

    # [분석 결과 반영] 데이터가 {'nodes': {'nodes': [...]}} 구조입니다.
    # outer_nodes는 {'schema_version': '1.0', ..., 'nodes': [...]} 딕셔너리입니다.
    outer_nodes = rds_normalized_data.get("nodes", {})
    
    # 실제 노드 리스트는 outer_nodes 안에 있는 'nodes' 키에 들어있습니다.
    if isinstance(outer_nodes, dict):
        nodes_payload = outer_nodes.get("nodes", [])
        account_id = outer_nodes.get("account_id", "288528695623")
    else:
        # 혹시나 예외적으로 바로 리스트인 경우 대응
        nodes_payload = outer_nodes if isinstance(outer_nodes, list) else []
        account_id = "288528695623"

    graph_data = {
        "schema_version": "1.0",
        "account_id": account_id,
        "nodes": [],
        "edges": []
    }

    # 2. 노드 처리
    for node in nodes_payload:
        n_type = node.get("node_type")
        n_id = node.get("node_id")
        res_id = node.get("resource_id")
        region = node.get("region", "us-east-1")
        attrs = node.get("attributes", {})
        rels = node.get("relationships", {})

        if n_type == "rds_instance":
            # Linker가 인식할 수 있도록 subnet 정보 포함
            subnet_ids = attrs.get("subnets", []) or rels.get("subnet_ids", [])
            
            graph_data["nodes"].append({
                "id": n_id,
                "type": "rds_instance",
                "name": node.get("name") or res_id,
                "arn": attrs.get("arn") or rels.get("db_instance_arn"),
                "region": region,
                "properties": {
                    "engine": f"{attrs.get('engine')}:{attrs.get('engine_version')}",
                    "status": attrs.get("status"),
                    "subnets": subnet_ids # 이 필드가 있어야 Linker가 Subnet과 연결합니다.
                }
            })
            
            # VPC 연결 엣지
            vpc_id = rels.get("vpc_id")
            if vpc_id:
                graph_data["edges"].append({
                    "id": f"edge:{res_id}:MEMBER_OF:{vpc_id}",
                    "relation": "MEMBER_OF",
                    "src": n_id,
                    "dst": f"{account_id}:{region}:vpc:{vpc_id}",
                    "directed": True
                })

    return graph_data