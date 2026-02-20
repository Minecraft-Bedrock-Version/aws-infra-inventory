from __future__ import annotations
from typing import Any, Dict, List

def graph_route_table(raw_payload: Dict[str, Any], account_id: str, region: str) -> List[Dict[str, Any]]:
    edges = [] 
    seen_edges = set() # 중복 방지

    # 서비스 node들 모두 미리 불러와두기
    route_tables_nodes = raw_payload.get("vpc", {}).get("route_tables", [])
    subnets_nodes = raw_payload.get("vpc", {}).get("subnets", []) 
    igws_nodes = raw_payload.get("vpc", {}).get("internet_gateways", [])

    for rt_value in route_tables_nodes: # 라우팅 테이블 목록 순회
        rt_id = rt_value.get("RouteTableId") # 라우팅 테이블 ID 추출
        vpc_id = rt_value.get("VpcId") # 속한 VPC ID 추출
        rt_node_id = f"{account_id}:{region}:route_table:{rt_id}" # 라우팅 테이블 노드 ID 정의

        # (1) 라우팅 테이블이 인터넷 게이트웨이로 경로를 가짐 (RT_ROUTES_TO_IGW)
        for route in rt_value.get("Routes", []): # 라우팅 규칙들 순회
            igw_id = route.get("GatewayId") # 대상 게이트웨이 ID 추출
            if igw_id and igw_id.startswith("igw-"): # 대상이 인터넷 게이트웨이라면
                edge_id = f"edge:{rt_id}:ROUTES_TO:{igw_id}" # 엣지 ID 정의
                
                if edge_id not in seen_edges: 
                    seen_edges.add(edge_id)
                    edges.append({
                        "id": edge_id,
                        "relation": "RT_ROUTES_TO_IGW",
                        "src": rt_node_id,
                        "dst": f"{account_id}:{region}:igw:{gw_id}",
                        "directed": True,
                        "conditions": f"This Route Table directs traffic for {route.get('DestinationCidrBlock')} to the Internet Gateway."
                    })

        # (2) 라우팅 테이블이 특정 서브넷에 적용됨 (RT_ASSOCIATED_WITH_SUBNET)
        for assoc in rt_value.get("Associations", []): # 연결(Association) 정보 확인
            subnet_id = assoc.get("SubnetId") # 연결된 서브넷 ID 추출
            if subnet_id: # 서브넷 ID가 존재한다면
                edge_id = f"edge:{rt_id}:ASSOCIATED_WITH:{subnet_id}"
                
                if edge_id not in seen_edges:
                    seen_edges.add(edge_id)
                    edges.append({
                        "id": edge_id,
                        "relation": "RT_ASSOCIATED_WITH_SUBNET",
                        "src": rt_node_id, 
                        "dst": f"{account_id}:{region}:subnet:{subnet_id}",
                        "directed": True,
                        "conditions": "This Route Table defines the networking rules for all resources within this subnet."
                    })

        # (3) 라우팅 테이블이 특정 VPC에 속함 (RT_BELONGS_TO_VPC)
        if vpc_id: # VPC ID 정보가 있다면
            edge_id = f"edge:{rt_id}:BELONGS_TO_VPC:{vpc_id}"
            if edge_id not in seen_edges:
                seen_edges.add(edge_id)
                edges.append({
                    "id": edge_id,
                    "relation": "RT_BELONGS_TO_VPC",
                    "src": rt_node_id, # 라우팅 테이블이 주체
                    "dst": f"{account_id}:{region}:vpc:{vpc_id}", # VPC가 대상
                    "directed": True,
                    "conditions": "This Route Table is created within and managed by the specified VPC."
                })

    return edges
