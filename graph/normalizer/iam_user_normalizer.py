from datetime import datetime, timezone

# 1. Statement 데이터 규격화 (Action/Resource 리스트 변환)
def normalize_statements(statements):
    normalized = []

    for s in statements:
        action = s.get("Action", [])
        resource = s.get("Resource", [])

        # 단일 문자열인 경우 리스트로 통일
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


# 2. Policy 리스트 정규화 (이름, ARN, Statement 추출)
def normalize_policy_list(policies):
    normalized = []

    for p in policies:
        normalized.append({
            "PolicyName": p.get("policy_name"),
            "PolicyArn": p.get("policy_arn"),
            "Statement": normalize_statements(p.get("statement", []))
        })

    return normalized


# 3. IAM User 데이터 노드 생성 (전체 데이터 구조화)
def normalize_iam_users(raw_payload, account_id, region="global"):
    items = raw_payload.get("iam_users", [])
    nodes = []

    for item in items:
        user = item["user"]
        user_id = user["UserId"]
        user_name = user["UserName"]

        # 노드 공통 데이터 구성
        node = {
            "node_type": "iam_user",
            "node_id": f"{account_id}:{region}:iam_user:{user_id}",
            "resource_id": user_id,
            "name": user_name,
            
            # 세부 속성 정의
            "attributes": {
                "arn": user["Arn"],
                "create_date": user["CreateDate"].isoformat(),
                
                "attached_policies": normalize_policy_list(
                    item.get("attached_policies", [])
                ),
                "inline_policies": normalize_policy_list(
                    item.get("inline_policies", [])
                ),
                "group_policies": normalize_policy_list(
                    item.get("group_policies", [])
                )
            },

            # 메타데이터 정보
            "raw_refs": {
                "source": sorted(list(set(item.get("api_sources", [])))),
                "collected_at": item.get("collected_at")
            }
        }

        nodes.append(node)

    return nodes
