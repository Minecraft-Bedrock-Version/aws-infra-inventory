from __future__ import annotations
from typing import Any, Dict, List

def graph_vpc(raw_payload: Dict[str, Any], account_id: str, region: str) -> List[Dict[str, Any]]:

    edges = []
    seen_edges = set() # 중복 방지

    #현재 구현된 서비스들의 node들 모두 미리 불러와두기
    vpcs_nodes = raw_payload.get("vpc", {}).get("vpcs", [])
    subnets_nodes = raw_payload.get("vpc", {}).get("subnets", [])
    igws_nodes = raw_payload.get("vpc", {}).get("internet_gateways", [])
    route_tables_nodes = raw_payload.get("vpc", {}).get("route_tables", [])
    security_groups_nodes = raw_payload.get("vpc", {}).get("security_groups", [])
    ec2_instances = raw_payload.get("ec2", {}).get("instances", [])

    for vpc_value in vpcs_nodes: #VPC 순회하면서
        vpc_id = vpc_value.get("VpcId") #VPC 고유 ID 추출
        vpc_node_id = f"{account_id}:{region}:vpc:{vpc_id}" #VPC 노드 ID 정의 

        # (1) VPC가 Subnet을 소유함 (VPC_HAS_SUBNET)
        for subnet in subnets_nodes: #Subnet 순회하면서
            if subnet.get("VpcId") == vpc_id: # 현재 VPC 소속의 서브넷이라면
                subnet_id = subnet.get("SubnetId") #해당 서브넷 ID 추출
                edge_id = f"edge:{vpc_id}:HAS_SUBNET:{subnet_id}"
                
                if edge_id not in seen_edges: 
                    seen_edges.add(edge_id)
                    edges.append({
                        "id": edge_id,
                        "relation": "VPC_HAS_SUBNET",
                        "src": vpc_node_id, 
                        "dst": f"{account_id}:{region}:subnet:{subnet_id}", # 서브넷이 대상 (Destination)
                        "directed": True,
                        "conditions": "This VPC manages and contains this subnet as a logical partition of its network."
                    })

        # (2) VPC가 Internet Gateway와 연결됨 (VPC_USES_IGW)
        for igw in igws_nodes: # IGW 순회하면서
            for attachment in igw.get("Attachments", []): #연결 정보 확인
                if attachment.get("VpcId") == vpc_id: # VPC에 연결된 IGW라면
                    igw_id = igw.get("InternetGatewayId") #IGW ID 추출
                    edge_id = f"edge:{vpc_id}:USES_IGW:{igw_id}"
                    
                    if edge_id not in seen_edges:
                        seen_edges.add(edge_id)
                        edges.append({
                            "id": edge_id,
                            "relation": "VPC_USES_IGW",
                            "src": vpc_node_id, 
                            "dst": f"{account_id}:{region}:igw:{igw_id}",
                            "directed": True,
                            "conditions": "This VPC is connected to the Internet Gateway to enable external communication."
                        })

        # (3) VPC가 Security Group을 포함함 (VPC_HAS_SG)
        for sg in security_groups_nodes: #보안그룹 순회하면서
            if sg.get("VpcId") == vpc_id: #이 VPC 범위 내의 SG라면
                sg_id = sg.get("GroupId") #SG ID 추출
                edge_id = f"edge:{vpc_id}:HAS_SG:{sg_id}"
                
                if edge_id not in seen_edges:
                    seen_edges.add(edge_id)
                    edges.append({
                        "id": edge_id,
                        "relation": "VPC_HAS_SG",
                        "src": vpc_node_id, 
                        "dst": f"{account_id}:{region}:security_group:{sg_id}",
                        "directed": True,
                        "conditions": "This VPC owns this Security Group to enforce network security policies."
                    })

        # (4) VPC가 Route Table을 관리함 (VPC_HAS_RT)
        for rt in route_tables_nodes: # 라우팅 테이블 순회
            if rt.get("VpcId") == vpc_id: # 이 VPC 전용 라우팅 테이블이라면
                rt_id = rt.get("RouteTableId") # RT ID 추출
                edge_id = f"edge:{vpc_id}:HAS_RT:{rt_id}"
                
                if edge_id not in seen_edges:
                    seen_edges.add(edge_id)
                    edges.append({
                        "id": edge_id,
                        "relation": "VPC_HAS_RT",
                        "src": vpc_node_id,
                        "dst": f"{account_id}:{region}:route_table:{rt_id}",
                        "directed": True,
                        "conditions": "This VPC uses this Route Table to determine where network traffic is directed."
                    })

        # (5) VPC가 EC2 인스턴스를 포함함 (VPC_HAS_INSTANCE)
        for instance in ec2_instances: # EC2 순회하면서
            if instance.get("VpcId") == vpc_id: # EC2가 속한 VPC ID가 일치하면
                instance_id = instance.get("InstanceId") #EC2 인스턴스 ID 추출
                edge_id = f"edge:{vpc_id}:HAS_INSTANCE:{instance_id}"
                
                if edge_id not in seen_edges:
                    seen_edges.add(edge_id)
                    edges.append({
                        "id": edge_id,
                        "relation": "VPC_HAS_INSTANCE",
                        "src": vpc_node_id,
                        "dst": f"{account_id}:{region}:ec2:{instance_id}",
                        "directed": True,
                        "conditions": "This VPC provides the primary network container for this EC2 instance."
                    })

    return edges
