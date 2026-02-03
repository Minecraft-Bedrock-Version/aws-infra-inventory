from __future__ import annotations
from typing import Any, Dict

def normalize_route_tables(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    #Node 생성
    route_tables = raw_payload.get("RouteTables", [])
    nodes = []
    for route_value in route_tables:
        tags = route_value.get("Tags", [])
        associations = route_value.get("Associations")
        
        #각 필드를 채우기 위한 값
        node_type = "route_table"
        route_id = route_value.get("RouteTableId")
        node_id = f"{account_id}:{region}:{node_type}:{route_id}"
        #resoucre id == route id
        name = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), None)
        vpc_id = route_value.get("VpcId")
        main = associations[0].get("Main")

        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": route_id,
            "name": name or route_id,
            "attributes": {
                "vpc_id": vpc_id,
                "main": main
            }
        }
        nodes.append(node)
    
    return nodes
