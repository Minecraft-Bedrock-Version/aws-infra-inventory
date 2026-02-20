from __future__ import annotations
from typing import Any, Dict, List

def graph_security_group(raw_payload: Dict[str, Any], account_id: str, region: str) -> List[Dict[str, Any]]:
    edges = [] 
    seen_edges = set() # 중복 방지

    # 서비스 node들 모두 미리 불러와두기
    security_groups_nodes = raw_payload.get("vpc", {}).get("security_groups", []) # 보안 그룹 목록
    ec2_instances = raw_payload.get("ec2", {}).get("instances", []) # EC2 인스턴스 목록 (적용 대상 확인용)

    for sg_value in security_groups_nodes: # 보안 그룹 목록 순회
        sg_id = sg_value.get("GroupId") # 보안 그룹 고유 ID 추출
        vpc_id = sg_value.get("VpcId") # 속한 VPC ID 추출
        sg_node_id = f"{account_id}:{region}:security_group:{sg_id}" # 보안 그룹 노드 ID 정의

        # (1) 보안 그룹이 특정 EC2 인스턴스에 적용됨 (SG_APPLIED_TO_INSTANCE)
        for instance in ec2_instances: # EC2 인스턴스 순회하면서
            # 인스턴스에 설정된 보안 그룹 리스트 확인
            sg_ids_in_instance = [sg.get("GroupId") for sg in instance.get("SecurityGroups", [])]
            
            if sg_id in sg_ids_in_instance: # 현재 SG가 인스턴스에 적용되어 있다면
                instance_id = instance.get("InstanceId") # 해당 인스턴스 ID 추출
                edge_id = f"edge:{sg_id}:APPLIED_TO:{instance_id}" # 엣지 ID 정의
                
                if edge_id not in seen_edges: # 아직 등록되지 않은 엣지라면
                    seen_edges.add(edge_id) # 중복 방지 셋에 추가
                    edges.append({
                        "id": edge_id,
                        "relation": "SG_APPLIED_TO_INSTANCE",
                        "src": sg_node_id, 
                        "dst": f"{account_id}:{region}:ec2:{instance_id}", # EC2 인스턴스가 대상
                        "directed": True,
                        "conditions": "This Security Group acts as a stateful firewall controlling traffic for this instance."
                    })

        # (2) 보안 그룹이 특정 VPC 내에 존재함 (SG_BELONGS_TO_VPC)
        if vpc_id: # VPC ID 정보가 존재한다면
            edge_id = f"edge:{sg_id}:BELONGS_TO_VPC:{vpc_id}"
            if edge_id not in seen_edges:
                seen_edges.add(edge_id)
                edges.append({
                    "id": edge_id,
                    "relation": "SG_BELONGS_TO_VPC",
                    "src": sg_node_id, 
                    "dst": f"{account_id}:{region}:vpc:{vpc_id}", 
                    "directed": True,
                    "conditions": "This Security Group is defined within the network boundaries of this VPC."
                })

    return edges
