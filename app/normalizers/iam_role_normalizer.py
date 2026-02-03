from __future__ import annotations
from typing import Any, Dict

def normalize_iam_roles(raw_payload: Dict[str, Any], account_id: str, region="global") -> Dict[str, Any]:
    roles = raw_payload.get("roles",[])
    nodes = []

    for role_value in roles:
        name = role_value.get("RoleName")
        
        node_type = "iam_role"
        node_id = f"{account_id}:{node_type}:{name}"
        resource_id = role_value.get("RoleId")
        arn = role_value.get("Arn")
        create_date = role_value.get("CreateDate")
        assume_role_policy = role_value.get("AssumeRolePolicyDocument",[])
        attached_policies = role_value.get("AttachedPolicies", [])
        inline_policies = role_value.get("InlinePolicies", [])

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
                "assume_role_policy": assume_role_policy,
                "attached_policies": attached_policies,
                "inline_policies": inline_policies
            }
        }

        nodes.append(node)

    return nodes