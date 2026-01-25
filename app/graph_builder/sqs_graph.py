import json
from typing import Any, Dict, List

def transform_sqs_to_graph(sqs_normalized_data: Any) -> Dict[str, Any]:
    # 1. [방어 로직] 문자열 에러('str' object has no attribute 'get') 방지
    curr = sqs_normalized_data
    try:
        for _ in range(3):
            if isinstance(curr, (str, bytes)):
                curr = json.loads(curr)
            else:
                break
    except Exception:
        return {"nodes": [], "edges": []}

    if not isinstance(curr, dict):
        return {"nodes": [], "edges": []}

    # 2. [구조 보정] 중첩된 {'nodes': {'nodes': [...]}} 구조 대응
    outer_nodes = curr.get("nodes", {})
    if isinstance(outer_nodes, dict):
        nodes_payload = outer_nodes.get("nodes", [])
        account_id = outer_nodes.get("account_id", curr.get("account_id", "unknown"))
    else:
        nodes_payload = outer_nodes if isinstance(outer_nodes, list) else []
        account_id = curr.get("account_id", "unknown")

    graph_data = {
        "schema_version": "1.0",
        "collected_at": curr.get("collected_at") if isinstance(curr, dict) else None,
        "account_id": account_id,
        "nodes": [],
        "edges": []
    }

    # 3. 노드 처리 루프
    for node in nodes_payload:
        if not isinstance(node, dict): continue
        
        n_id = node.get("node_id")
        res_id = node.get("resource_id")
        # n_id가 문자열이 아닐 경우를 대비한 안전한 region 추출
        region = "us-east-1"
        if n_id and ":" in str(n_id):
            parts = str(n_id).split(":")
            if len(parts) > 1: region = parts[1]
            
        attrs = node.get("attributes", {})
        rels = node.get("relationships", {})

        # 3-1. SQS 노드 생성
        new_node = {
            "id": n_id,
            "type": "sqs",
            "name": node.get("name") or res_id,
            "arn": attrs.get("arn") or rels.get("queue_arn"),
            "region": region,
            "properties": {
                "queue_url": attrs.get("queue_url"),
                "visibility_timeout": attrs.get("visibility_timeout"),
                "delay_seconds": attrs.get("delay_seconds"),
                "sse_enabled": attrs.get("sse_enabled", False)
            }
        }
        graph_data["nodes"].append(new_node)

        # 3-2. 동적 관계 형성 (하드코딩 대신 관계 데이터 활용)
        # SQS가 Lambda 매핑과 연결되어 있다면 (relationships 활용)
        mapping_id = rels.get("event_source_mapping_id")
        if mapping_id:
            graph_data["edges"].append({
                "id": f"edge:sqs:{res_id}:TRIGGER:{mapping_id}",
                "relation": "INVOKES",
                "src": n_id,
                "dst": f"{account_id}:{region}:lambda_event_source_mapping:{mapping_id}",
                "directed": True
            })

    return graph_data