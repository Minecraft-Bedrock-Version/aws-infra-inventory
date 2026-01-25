from datetime import datetime, timezone

def normalize_statements(statements):

    normalized = []

    for s in statements:
        action = s.get("Action", [])
        resource = s.get("Resource", [])

        if isinstance(action, str):
            action = [action]

        if isinstance(resource, str):
            resource = [resource]
        
        # Resource가 없으면 wildcard로 설정
        if not resource:
            resource = ["*"]

        normalized.append({
            "Effect": s.get("Effect"),
            "Action": action,
            "Resource": resource
        })

    return normalized


def normalize_policy_list(policies):

    normalized = []

    for p in policies:
        normalized.append({
            "PolicyName": p.get("policy_name"),
            "PolicyArn": p.get("policy_arn"),
            "Statement": normalize_statements(p.get("statement", []))
        })

    return normalized


def normalize_iam_roles(items, account_id, region="global"):

    nodes = []

    for item in items:
        role = item["role"]

        role_id = role["RoleId"]
        role_name = role["RoleName"]

        node = {
            "node_type": "iam_role",
            "node_id": f"{account_id}:{region}:iam_role:{role_id}",
            "resource_id": role_id,
            "name": role_name,

            "attributes": {
                "arn": role["Arn"],
                "assume_role_policy": role.get("AssumeRolePolicyDocument"),
                
                "inline_policies": normalize_policy_list(
                    item.get("inline_policies", [])
                ),

                "attached_policies": normalize_policy_list(
                    item.get("attached_policies", [])
                )
            },

            "raw_refs": {
                "source": sorted(list(set(item.get("api_sources", [])))),
                "collected_at": item.get("collected_at")
            }
        }

        nodes.append(node)

    return nodes
