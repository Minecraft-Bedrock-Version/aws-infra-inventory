import re
from typing import Dict, List, Any

def parse_region_from_node_id(node_id: str) -> str:
    parts = node_id.split(":")
    return parts[1] if len(parts) >= 2 else "global"

def extract_role_name_from_arn(arn: str) -> str:
    if not arn or not isinstance(arn, str):
        return "unknown"
    return arn.split("/")[-1]

def build_iam_role_node_id(account_id: str, role_name: str) -> str:
    # Linker가 인식하는 표준 IAM Role ID 형식으로 생성
    return f"{account_id}:global:iam_role:{role_name}"

def transform_iam_users(normalized: Dict[str, Any]) -> Dict[str, Any]:
    graph_nodes: List[Dict[str, Any]] = []
    graph_edges: List[Dict[str, Any]] = []

    # normalized 데이터가 문자열일 경우 처리 (방어 로직)
    if isinstance(normalized, str):
        import json
        try: normalized = json.loads(normalized)
        except: return {"nodes": [], "edges": []}

    account_id = normalized.get("account_id", "288528695623")
    collected_at = normalized.get("collected_at")

    # 데이터 계층 대응 (중첩 구조 확인)
    nodes_payload = normalized.get("nodes", [])
    if isinstance(nodes_payload, dict):
        nodes_payload = nodes_payload.get("nodes", [])

    for node in nodes_payload:
        if not isinstance(node, dict) or node.get("node_type") != "iam_user":
            continue

        node_id = node["node_id"]
        resource_id = node["resource_id"]
        user_name = node.get("name")
        region = parse_region_from_node_id(node_id)
        
        # [핵심] attributes와 properties에서 모든 정책 데이터를 끌어모음
        attrs = node.get("attributes", {})
        props = node.get("properties", {})
        
        # 두 곳의 정책을 합쳐서 누락 방지
        inline_policies = attrs.get("inline_policies", []) or props.get("inline_policies", [])
        attached_policies = attrs.get("attached_policies", []) or props.get("attached_policies", [])
        group_policies = attrs.get("group_policies", []) or props.get("group_membership", [])

        # 1. IAM User 노드 생성
        graph_node = {
            "id": node_id,
            "type": "iam_user",
            "name": user_name,
            "arn": attrs.get("arn") or f"arn:aws:iam::{account_id}:user/{user_name}",
            "region": region,
            "properties": {
                "create_date": attrs.get("create_date"),
                # Linker가 이 필드를 읽어서 AssumeRole 경로를 계산함
                "inline_policies": inline_policies,
                "attached_policies": attached_policies,
                "group_membership": group_policies
            }
        }
        graph_nodes.append(graph_node)

        # 2. Inline Policy 분석: CAN_ASSUME_ROLE (명시적 ARN인 경우만 직접 생성)
        for policy in inline_policies:
            policy_name = policy.get("PolicyName", "UnnamedPolicy")
            statements = policy.get("Statement", [])
            if isinstance(statements, dict): statements = [statements]

            for stmt in statements:
                actions = stmt.get("Action", [])
                if isinstance(actions, str): actions = [actions]

                # AssumeRole 권한 확인
                if any(a in actions for a in ["sts:AssumeRole", "sts:*", "*"]):
                    resources = stmt.get("Resource", [])
                    if isinstance(resources, str): resources = [resources]
                    
                    for role_arn in resources:
                        # '*'인 경우 여기서 멈추지 않고, properties에 담긴 정보를 토대로
                        # Linker가 전체 Role과 자동으로 엣지를 맺도록 유도함
                        if role_arn == "*":
                            continue
                        
                        # 특정 ARN이 명시된 경우에만 직접 엣지 생성
                        if "arn:aws:iam" in role_arn:
                            role_name = extract_role_name_from_arn(role_arn)
                            dst_role_id = build_iam_role_node_id(account_id, role_name)

                            graph_edges.append({
                                "id": f"edge:{user_name}:CAN_ASSUME_ROLE:{role_name}",
                                "relation": "CAN_ASSUME_ROLE",
                                "src": node_id,
                                "src_label": f"iam_user:{user_name}",
                                "dst": dst_role_id,
                                "dst_label": f"iam_role:{role_name}",
                                "directed": True,
                                "conditions": [{"key": "policy_type", "value": "inline"}]
                            })

        # 3. Attached Policy 분석 (HAS_POLICY)
        for policy in attached_policies:
            p_name = policy.get("PolicyName")
            p_arn = policy.get("PolicyArn", "")
            if not p_name: continue

            prefix = "aws" if ":aws:policy" in p_arn else account_id
            dst_policy_id = f"{prefix}:global:iam_policy:{p_name}"

            graph_edges.append({
                "id": f"edge:{user_name}:HAS_POLICY:{p_name}",
                "relation": "HAS_POLICY",
                "src": node_id,
                "src_label": f"iam_user:{user_name}",
                "dst": dst_policy_id,
                "dst_label": f"iam_policy:{p_name}",
                "directed": True
            })

    return {
        "schema_version": "1.0",
        "collected_at": collected_at,
        "account_id": account_id,
        "nodes": graph_nodes,
        "edges": graph_edges
    }