import re
from typing import Dict, List, Any

# 리전 정보 추출
def parse_region_from_node_id(node_id: str) -> str:
    parts = node_id.split(":")
    return parts[1] if len(parts) >= 2 else "global"

# 리소스 이름 추출
def extract_role_name_from_arn(arn: str) -> str:
    if not arn or not isinstance(arn, str):
        return "unknown"
    return arn.split("/")[-1]

# Node ID 생성 
def build_iam_role_node_id(account_id: str, role_name: str) -> str:
    return f"{account_id}:global:iam_role:{role_name}"

def transform_iam_users(normalized: Dict[str, Any]) -> Dict[str, Any]:
    graph_nodes: List[Dict[str, Any]] = []
    graph_edges: List[Dict[str, Any]] = []

    account_id = normalized.get("account_id", "unknown")
    collected_at = normalized.get("collected_at")

    for node in normalized.get("nodes", []):
        if node.get("node_type") != "iam_user":
            continue

        node_id = node["node_id"]
        resource_id = node["resource_id"]
        user_name = node.get("name")
        region = parse_region_from_node_id(node_id)
        attrs = node.get("attributes", {})

        # 1. IAM User 노드 생성
        graph_node = {
            "id": node_id,
            "type": "iam_user",
            "name": user_name,
            "arn": attrs.get("arn"),
            "region": region,
            "properties": {
                "create_date": attrs.get("create_date"),
                "inline_policies": attrs.get("inline_policies", []),
                "attached_policies": attrs.get("attached_policies", []),
                "group_membership": attrs.get("group_policies", []),
            }
        }
        graph_nodes.append(graph_node)

        # 2. Inline Policy 분석: CAN_ASSUME_ROLE 관계 추출
        for policy in attrs.get("inline_policies", []):
            policy_name = policy.get("PolicyName")
            for stmt in policy.get("Statement", []):

                actions = stmt.get("Action", [])
                if isinstance(actions, str):
                    actions = [actions]

                # AssumeRole 권한이 있는지 확인
                if any(a in actions for a in ["sts:AssumeRole", "sts:*", "*"]):
                    resources = stmt.get("Resource", [])
                    if isinstance(resources, str):
                        resources = [resources]
                    
                    for role_arn in resources:
                        if role_arn == "*":
                            continue
                        
                        role_name = extract_role_name_from_arn(role_arn)
                        dst_role_id = build_iam_role_node_id(account_id, role_name)

                        graph_edges.append({
                            "id": f"edge:{resource_id}:CAN_ASSUME_ROLE:{role_name}",
                            "relation": "CAN_ASSUME_ROLE",
                            "src": node_id,
                            "src_label": f"iam_user:{user_name}",
                            "dst": dst_role_id,
                            "dst_label": f"iam_role:{role_name}",
                            "directed": True,
                            "conditions": [
                                {"key": "policy_type", "value": "inline"},
                                {"key": "policy_name", "value": policy_name}
                            ]
                        })

        # 3. Attached Policy 분석: HAS_POLICY 관계 생성
        for policy in attrs.get("attached_policies", []):
            p_name = policy.get("PolicyName")
            p_arn = policy.get("PolicyArn", "")

            # AWS 관리형 정책과 고객 관리형 정책 구분하여 ID 생성
            prefix = "aws" if ":aws:policy" in p_arn else account_id
            dst_policy_id = f"{prefix}:global:iam_policy:{p_name}"

            graph_edges.append({
                "id": f"edge:{resource_id}:HAS_POLICY:{p_name}",
                "relation": "HAS_POLICY",
                "src": node_id,
                "src_label": f"iam_user:{user_name}",
                "dst": dst_policy_id,
                "dst_label": f"iam_policy:{p_name}",
                "directed": True,
                "conditions": [
                    {"key": "policy_arn", "value": p_arn}
                ]
            })

        # 4. Group Policy 분석: MEMBER_OF_GROUP 관계 생성
        processed_groups = set()
        for g_policy in attrs.get("group_policies", []):
            g_name = g_policy.get("group_name")
            if g_name and g_name not in processed_groups:
                dst_group_id = f"{account_id}:global:iam_group:{g_name}"
                
                graph_edges.append({
                    "id": f"edge:{resource_id}:MEMBER_OF:{g_name}",
                    "relation": "MEMBER_OF",
                    "src": node_id,
                    "src_label": f"iam_user:{user_name}",
                    "dst": dst_group_id,
                    "dst_label": f"iam_group:{g_name}",
                    "directed": True
                })
                processed_groups.add(g_name)

    return {
        "schema_version": "1.0",
        "collected_at": collected_at,
        "account_id": account_id,
        "nodes": graph_nodes,
        "edges": graph_edges
    }


if __name__ == "__main__":
    import json
    try:
        with open("iam_user_normalized.json", "r") as f:
            data = json.load(f)
            result = transform_iam_users(data)
            print(json.dumps(result, indent=2, ensure_ascii=False))
    except FileNotFoundError:
        print("테스트 파일이 없습니다.")
