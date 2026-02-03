from __future__ import annotations
from typing import Any, Dict

def normalize_igws(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    #Node 생성
    igws = raw_payload.get("InternetGateways", [])
    nodes = []
    for igw_value in igws:
        tags = igw_value.get("Tags", [])
        attached = igw_value.get("Attachments")
        
        #각 필드를 채우기 위한 값
        node_type = "igw"
        igw_id = igw_value.get("InternetGatewayId")
        node_id = f"{account_id}:{region}:{node_type}:{igw_id}"
        #resoucre id == igw id
        name = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), None)
        attached_vpc_id = attached[0].get("VpcId")
        state = attached[0].get("State")

        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": igw_id,
            "name": name or igw_id,
            "attributes": {
                "attached_vpc_id": attached_vpc_id,
                "state": state
            }
        }
        nodes.append(node)
    
    return nodes
