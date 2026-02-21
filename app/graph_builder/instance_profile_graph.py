from __future__ import annotations
from typing import Any, Dict, List

def graph_instance_profile(raw_payload: Dict[str, Any], account_id: str, region: str) -> List[Dict[str, Any]]:
    edges = []
    seen_edges = set() # 중복 방지

    #현재 구현된 서비스들의 node들 모두 미리 불러와두기
    ip_data = raw_payload.get("iam_instance_profile", {}).get("instance_profiles", [])
    iam_roles = raw_payload.get("iam_role", {}).get("roles", [])
    iam_users = raw_payload.get("iam_user", {}).get("users", [])
    ec2_instances = raw_payload.get("ec2", {}).get("instances", [])

    for ip_value in ip_data:
        ip_name = ip_value.get("InstanceProfileName")
        ip_node_id = f"{account_id}:iam_instance_profile:{ip_name}"

        # (1) 인스턴스 프로파일이 role과 연결됨 (IP_HAS_ROLE)
        for role_info in ip_value.get("Roles", []): #인스턴스프로파일 객체 속 role 정보를 순회하면서
            role_name = role_info.get("RoleName") #role 이름을 추출
            role_resource_id = role_info.get("RoleId") #role 리소스 ID 추출
            role_node_id = f"{account_id}:iam_role:{role_name}"
            
            edge_id = f"edge:{ip_name}:HAS_ROLE:{role_name}"
            if edge_id not in seen_edges:
                seen_edges.add(edge_id)
                edges.append({
                    "id": edge_id,
                    "relation": "INSTANCE_PROFILE_HAS_ROLE",
                    "src": ip_node_id,
                    "dst": role_node_id,
                    "directed": True,
                    "conditions": "This instance profile acts as a container for the IAM Role, allowing it to be passed to EC2."
                })

        # (3) 인스턴스프로파일이 EC2와 연결됨 (IP_ATTACHED_TO_EC2)
        for instance in ec2_instances: #EC2 인스턴스 순회하면서
            iam_ip_info = instance.get("IamInstanceProfile") #연결된 프로파일 정보 추출
            if iam_ip_info: #프로파일이 연결되어 있으면
                attached_ip_name = iam_ip_info.get("Arn", "").split('/')[-1] #arn에서 이름 추출
                
                if attached_ip_name == ip_name: #현재 프로파일과 일치하면
                    instance_id = instance.get("InstanceId")
                    instance_node_id = f"{account_id}:{region}:ec2_instance:{instance_id}"
                    
                    edge_id = f"edge:{ip_name}:ATTACHED_TO:{instance_id}"
                    if edge_id not in seen_edges:
                        seen_edges.add(edge_id)
                        edges.append({
                            "id": edge_id,
                            "relation": "INSTANCE_PROFILE_ATTACHED_TO_EC2",
                            "src": ip_node_id,
                            "dst": instance_node_id,
                            "directed": True,
                            "conditions": "This instance profile is currently associated with the EC2 instance, providing its IAM identity."
                        })

    return edges
