from __future__ import annotations
from typing import Any, Dict, List

def graph_subnet(raw_payload: Dict[str, Any], account_id: str, region: str) -> List[Dict[str, Any]]:
    edges = [] 
    seen_edges = set() # 중복 방지

    # 서비스 node들 모두 미리 불러와두기
    subnets_nodes = raw_payload.get("vpc", {}).get("subnets", [])
    route_tables_nodes = raw_payload.get("vpc", {}).get("route_tables", [])
    ec2_nodes = raw_payload.get("ec2", {}).get("instances", [])

    for subnet_value in subnets_nodes: # 서브넷 목록 순회
        subnet_id = subnet_value.get("SubnetId") # 서브넷 ID 추출
        vpc_id = subnet_value.get("VpcId") # 현재 서브넷이 속한 VPC ID 추출
        subnet_node_id = f"{account_id}:{region}:subnet:{subnet_id}" # 서브넷 노드 ID 정의

        # (1) Subnet이 VPC 속에 속함 (BELONGS_TO_VPC)
        if vpc_id: # 현재 서브넷에 VPC ID 정보가 있다면
            edge_id = f"edge:{subnet_id}:BELONGS_TO_VPC:{vpc_id}" # 엣지 ID 정의
            if edge_id not in seen_edges: # 아직 등록되지 않은 엣지라면
                seen_edges.add(edge_id) # 중복 방지 셋에 추가
                edges.append({
                    "id": edge_id,
                    "relation": "BELONGS_TO_VPC",
                    "src": subnet_node_id,
                    "dst": f"{account_id}:{region}:vpc:{vpc_id}", 
                    "directed": True,
                    "conditions": "This subnet is part of the VPC"
                })

        # (2) 서브넷이 라우팅 테이블에 연결됨 (ASSOCIATED_WITH_RT)
        for rt in route_tables_nodes: # 라우팅 테이블 순회하면서
            associations = rt.get("Associations", []) # 라우팅 테이블의 연결 정보 확인
            for assoc in associations: # 연결 정보 순회
                if assoc.get("SubnetId") == subnet_id: # 연결된 서브넷 ID가 현재 서브넷과 일치하면
                    rt_id = rt.get("RouteTableId") # 해당 라우팅 테이블 ID 추출
                    edge_id = f"edge:{subnet_id}:ASSOCIATED_WITH_RT:{rt_id}" # 엣지 ID 정의
                    
                    if edge_id not in seen_edges: # 아직 등록되지 않은 엣지라면
                        seen_edges.add(edge_id) # 중복 방지 셋에 추가
                        edges.append({
                            "id": edge_id,
                            "relation": "ASSOCIATED_WITH_RT",
                            "src": subnet_node_id, 
                            "dst": f"{account_id}:{region}:route_table:{rt_id}", 
                            "directed": True,
                            "conditions": "This subnet follows the routing rules defined in the associated Route Table to direct network traffic."
                        })

        # (3) 서브넷 내부에 EC2 인스턴스가 배치됨 (SUBNET_HAS_INSTANCE)
        for instance in ec2_nodes: # EC2 순회하면서
            if instance.get("SubnetId") == subnet_id: # EC2가 이 서브넷에 배치되었다면
                instance_id = instance.get("InstanceId") #EC2 인스턴스 ID 추출
                edge_id = f"edge:{subnet_id}:HAS_INSTANCE:{instance_id}"
                
                if edge_id not in seen_edges:
                    seen_edges.add(edge_id)
                    edges.append({
                        "id": edge_id,
                        "relation": "SUBNET_HAS_INSTANCE",
                        "src": subnet_node_id, 
                        "dst": f"{account_id}:{region}:ec2:{instance_id}", 
                        "directed": True,
                        "conditions": "This EC2 instance is hosted within the IP range of this subnet."
                    })

    return edges
