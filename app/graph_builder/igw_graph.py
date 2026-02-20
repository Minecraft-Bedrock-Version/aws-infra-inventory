from __future__ import annotations
from typing import Any, Dict, List

def graph_internet_gateway(raw_payload: Dict[str, Any], account_id: str, region: str) -> List[Dict[str, Any]]:
    edges = [] 
    seen_edges = set() # 중복 방지

    # 서비스 node들 모두 미리 불러와두기
    igws_nodes = raw_payload.get("vpc", {}).get("internet_gateways", []) # 인터넷 게이트웨이 목록
    vpcs_nodes = raw_payload.get("vpc", {}).get("vpcs", []) # VPC 목록 (연결 확인용)

    for igw_value in igws_nodes: # 인터넷 게이트웨이 목록 순회
        igw_id = igw_value.get("InternetGatewayId") # IGW 고유 ID 추출
        igw_node_id = f"{account_id}:{region}:igw:{igw_id}" # IGW 노드 ID 정의

        # (1) 인터넷 게이트웨이가 VPC에 연결됨 (IGW_ATTACHED_TO_VPC)
        for attachment in igw_value.get("Attachments", []): # 연결 정보 확인
            vpc_id = attachment.get("VpcId") # 연결된 VPC ID 추출
            state = attachment.get("State") # 연결 상태
            
            if vpc_id: # 연결된 VPC가 있다면
                edge_id = f"edge:{igw_id}:ATTACHED_TO:{vpc_id}" # 엣지 ID 정의
                
                if edge_id not in seen_edges: # 아직 등록되지 않은 엣지라면
                    seen_edges.add(edge_id) # 중복 방지 셋에 추가
                    edges.append({
                        "id": edge_id,
                        "relation": "IGW_ATTACHED_TO_VPC",
                        "src": igw_node_id, 
                        "dst": f"{account_id}:{region}:vpc:{vpc_id}", 
                        "directed": True,
                        "conditions": f"This IGW is {state} and provides internet access to the attached VPC."
                    })

    return edges
