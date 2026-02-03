from __future__ import annotations
from typing import Any, Dict

def normalize_iam_users(raw_payload: Dict[str, Any], account_id: str, region="global") -> Dict[str, Any]:
    users = raw_payload.get("users",[])
    nodes = []

    for user_value in users:
        name = user_value.get("UserName")
        
        node_type = "iam_user"
        node_id = f"{account_id}:{node_type}:{name}"
        resource_id = user_value.get("UserId")
        arn = user_value.get("Arn")
        create_date = user_value.get("CreateDate")
        attached_policies = user_value.get("AttachedPolicies", [])
        inline_policies = user_value.get("InlinePolicies", [])
        group_policies = user_value.get("Groups", [])

        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": resource_id,
            "name": name,
            "account_id": account_id,
            "region": region,
            "attributes": {
                "arn": arn,
                "create_date": create_date.isoformat(),
                "attached_policies": attached_policies,
                "inline_policies": inline_policies,
                "group_policies": group_policies
            }
        }

        nodes.append(node)

    return nodes