from datetime import datetime, timezone

# 1. Statement 규격화
def normalize_statements(statements):
    normalized = []

    for s in statements:
        action = s.get("Action", [])
        resource = s.get("Resource", [])

        if isinstance(action, str):
            action = [action]

        if isinstance(resource, str):
            resource = [resource]

        normalized.append({
            "Effect": s.get("Effect"),
            "Action": action,
            "Resource": resource
        })

    return normalized


# 2. Policy 리스트 정규화 
def normalize_policy_list(policies):
    normalized = []

    for p in policies:
        normalized.append({
            "PolicyName": p.get("policy_name"),
            "PolicyArn": p.get("policy_arn"),
            "Statement": normalize_statements(p.get("statement", []))
        })

    return normalized


# 3. IAM Role 데이터 노드 생성 
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

            # Role 고유 속성 (신뢰 관계 및 정책 리스트)
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

            # 데이터 출처 및 수집 정보
            "raw_refs": {
                "source": sorted(list(set(item.get("api_sources", [])))),
                "collected_at": item.get("collected_at")
            }
        }

        nodes.append(node)

    return nodes
