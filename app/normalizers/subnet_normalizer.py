from __future__ import annotations
from typing import Any, Dict

def normalize_subnets(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    #Node 생성
    subnets = raw_payload.get("Subnets", [])
    nodes = []
    for subnet_value in subnets:
        tags = subnet_value.get("Tags", [])
        
        #각 필드를 채우기 위한 값
        node_type = "subnet"
        subnet_id = subnet_value.get("SubnetId")
        node_id = f"{account_id}:{region}:{node_type}:{subnet_id}"
        #resoucre id == subnet id
        name = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), None)
        vpc_id = subnet_value.get("VpcId")
        cidr = subnet_value.get("CidrBlock")
        az = subnet_value.get("AvailabilityZone")

        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": subnet_id,
            "name": name or subnet_id,
            "attributes": {
                "vpc_id": vpc_id,
                "cidr": cidr,
                "az": az
            }
        }
        nodes.append(node)
    
    return nodes
