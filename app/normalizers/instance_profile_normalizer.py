from __future__ import annotations
from typing import Any, Dict, List
from datetime import timezone

def normalize_instance_profile(raw_payload: Dict[str, Any], account_id: str, region: str) -> List[Dict[str, Any]]:

    ip_data = raw_payload.get("iam_instance_profile", {})
    profiles = ip_data.get("instance_profiles", [])
    nodes = []

    for ip_value in profiles:
        ip_name = ip_value.get("InstanceProfileName")
        ip_id = ip_value.get("InstanceProfileId")
        arn = ip_value.get("Arn")
        path = ip_value.get("Path")
        
        raw_date = ip_value.get("CreateDate")
        create_date = raw_date.isoformat() if hasattr(raw_date, "isoformat") else str(raw_date) if raw_date else None
        
        # 이 프로파일에 연결된 IAM Role 정보
        roles = ip_value.get("Roles", [])
        bound_role_names = [r.get("RoleName") for r in roles]
        bound_role_arns = [r.get("Arn") for r in roles]

        node_type = "iam_instance_profile"
        node_id = f"{account_id}:iam_instance_profile:{ip_name}"

        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": ip_id,
            "name": ip_name,
            "account_id": account_id,
            "region": region,
            "attributes": {
                "arn": arn,
                "path": path,
                "create_date": create_date,
                "bound_roles": bound_role_names, # 연결된 Role 이름 리스트
                "bound_role_arns": bound_role_arns, # 연결된 Role ARN 리스트
                "is_attached": False # 수집 시점의 기본 상태
            }
        }
        nodes.append(node)

    return nodes
