import re
from typing import Dict, List, Any

def parse_region_from_node_id(node_id: str) -> str:
    parts = node_id.split(":")
    return parts[1] if len(parts) >= 4 else "global"


def extract_user_id_from_arn(arn: str) -> str:
    return arn.split("/")[-1]


def build_iam_user_node_id(account_id: str, user_name: str) -> str:
    return f"{account_id}:global:iam_user:{user_name}"


def transform_iam_roles(normalized: dict) -> dict:
    graph_nodes = []
    graph_edges = []

    account_id = normalized["account_id"]
    collected_at = normalized["collected_at"]

    for node in normalized["nodes"]:
        if node["node_type"] != "iam_role":
            continue

        node_id = node["node_id"]
        region = parse_region_from_node_id(node_id)
        attrs = node.get("attributes", {})

        role_name = node.get("name")
        role_resource_id = node.get("resource_id")

        graph_node = {
            "id": node_id,
            "type": "iam_role",
            "name": role_name,
            "arn": attrs.get("arn"),
            "region": region,
            "properties": {
                "assume_role_policy": attrs.get("assume_role_policy"),
                "inline_policies": attrs.get("inline_policies") or False,
                "attached_policies": attrs.get("attached_policies") or False,
            }
        }

        graph_nodes.append(graph_node)
        
        assume_policy = attrs.get("assume_role_policy", {})
        for stmt in assume_policy.get("Statement", []):
            action = stmt.get("Action")
            if action != "sts:AssumeRole":
                continue

            principal = stmt.get("Principal", {})

            if "AWS" in principal:
                principal_arn = principal["AWS"]
                user_name = extract_user_id_from_arn(principal_arn)
                user_node_id = build_iam_user_node_id(account_id, user_name)

                edge_id = f"edge:{user_name}:TRUSTED_BY:{role_name}"

                graph_edges.append({
                    "id": edge_id,
                    "relation": "TRUSTED_BY",
                    "src": user_node_id,
                    "src_label": f"iam_user:{user_name}",
                    "dst": node_id,
                    "dst_label": f"iam_role:{role_name}",
                    "directed": True,
                    "conditions": [
                        {"key": "action", "value": "sts:AssumeRole"}
                    ]
                })

            if "Service" in principal:
                service_name = principal["Service"]
                service_node_id = f"aws:global:service:{service_name}"

                edge_id = f"edge:{service_name}:CAN_ASSUME_ROLE:{role_name}"

                graph_edges.append({
                    "id": edge_id,
                    "relation": "CAN_ASSUME_ROLE",
                    "src": service_node_id,
                    "src_label": f"service:{service_name}",
                    "dst": node_id,
                    "dst_label": f"iam_role:{role_name}",
                    "directed": True,
                    "conditions": [
                        {"key": "action", "value": "sts:AssumeRole"}
                    ]
                })

        for policy in attrs.get("attached_policies", []):
            policy_name = policy.get("PolicyName")
            policy_arn = policy.get("PolicyArn")

            dst_node_id = f"aws:global:iam_policy:{policy_name}"
            edge_id = f"edge:{role_name}:HAS_POLICY:{policy_name}"

            graph_edges.append({
                "id": edge_id,
                "relation": "HAS_POLICY",
                "src": node_id,
                "src_label": f"iam_role:{role_name}",
                "dst": dst_node_id,
                "dst_label": f"iam_policy:{policy_name}",
                "directed": True,
                "conditions": [
                    {"key": "policy_arn", "value": policy_arn}
                ]
            })

        # Role의 권한 분석: 정책에서 서비스 접근 권한 추출
        inline_policies = attrs.get("inline_policies", []) or []
        for policy in inline_policies:
            policy_name = policy.get("PolicyName", "UnnamedPolicy")
            statements = policy.get("Statement", [])
            if isinstance(statements, dict): 
                statements = [statements]

            for stmt in statements:
                actions = stmt.get("Action", [])
                if isinstance(actions, str): 
                    actions = [actions]
                
                resources = stmt.get("Resource", [])
                if isinstance(resources, str): 
                    resources = [resources]

                # 액션에서 서비스 추출 (예: s3:GetObject -> s3)
                for action in actions:
                    if action == "*" or action == "":
                        continue
                    
                    service_name = action.split(":")[0]
                    if service_name and service_name != "*":
                        service_node_id = f"aws:global:service:{service_name}"
                        edge_id = f"edge:{role_name}:CAN_ACCESS_SERVICE:{service_name}"
                        
                        graph_edges.append({
                            "id": edge_id,
                            "relation": "CAN_ACCESS_SERVICE",
                            "src": node_id,
                            "src_label": f"iam_role:{role_name}",
                            "dst": service_node_id,
                            "dst_label": f"service:{service_name}",
                            "directed": True,
                            "conditions": [
                                {"key": "action", "value": action},
                                {"key": "resource", "value": ",".join(resources[:3])}
                            ]
                        })

    return {
        "schema_version": "1.0",
        "collected_at": collected_at,
        "account_id": account_id,
        "nodes": graph_nodes,
        "edges": graph_edges
    }
