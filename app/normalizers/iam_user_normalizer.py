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


def normalize_iam_users(raw_payload, account_id, region="global"):
    items = raw_payload
    nodes = []

    for item in items:
        user = item["user"]

        user_id = user["UserId"]
        user_name = user["UserName"]

        node = {
            "node_type": "iam_user",
            "node_id": f"iam_user:{account_id}:{user_name}",
            "resource_id": user_id,
            "name": user_name,
            
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

            "raw_refs": {
                "source": sorted(list(set(item.get("api_sources", [])))),
                "collected_at": item.get("collected_at")
            }
        }

        nodes.append(node)

    return nodes