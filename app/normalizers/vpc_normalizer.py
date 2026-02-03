from __future__ import annotations
from typing import Any, Dict

def normalize_vpcs(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    #Node 생성
    vpcs = raw_payload.get("Vpcs", [])
    nodes = []
    for vpc_value in vpcs:
        tags = vpc_value.get("Tags", [])
        
        #각 필드를 채우기 위한 값
        node_type = "vpc"
        vpc_id = vpc_value.get("VpcId")
        node_id = f"{account_id}:{region}:{node_type}:{vpc_id}"
        #resoucre id == vpc id
        name = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), None)
        default = vpc_value.get("IsDefault")
        cidr = vpc_value.get("CidrBlock")

        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": vpc_id,
            "name": name or vpc_id, # 이름이 없으면 ID라도 표시
            "attributes": {
                "cidr": cidr, 
                "default": default
            }
        }
        nodes.append(node)
    
    return nodes
