from __future__ import annotations
from typing import Any, Dict

def normalize_secretsmanager(raw_payload: Dict[str, Any], account_id: str, region="us-east-1") -> Dict[str, Any]:
    secrets = raw_payload.get("secrets", [])
    nodes = []

    #secretsmanager 노드
    for secret_value in secrets:
        name = secret_value.get("Name")
        
        node_type = "secretsmanager"
        node_id = f"{account_id}:{region}:{node_type}:{name}"
        arn = secret_value.get("ARN")
        create_date = secret_value.get("CreatedDate")
        description = secret_value.get("Description", "")
        resource_policy = secret_value.get("ResourcePolicy")
        versions_to_stages = secret_value.get("SecretVersionsToStages", {})
        tags = secret_value.get("Tags", [])

        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": name,
            "name": name,
            "account_id": account_id,
            "region": region,
            "attributes": {
                "arn": arn,
                "create_date": create_date.isoformat() if hasattr(create_date, 'isoformat') else create_date,
                "description": description,
                "resource_policy": resource_policy,
                "versions_to_stages": versions_to_stages,
                "tags": tags
            }
        }

        nodes.append(node)

    return nodes
