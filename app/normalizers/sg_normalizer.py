from __future__ import annotations
from typing import Any, Dict, List

def normalize_security_groups(raw_payload: Dict[str, Any], account_id: str, region: str) -> List[Dict[str, Any]]:
    #Node 생성
    security_groups = raw_payload.get("SecurityGroups", [])
    nodes = []
    
    for sg_value in security_groups:
        tags = sg_value.get("Tags", [])
        
        #각 필드를 채우기 위한 값
        node_type = "security_group"
        group_id = sg_value.get("GroupId")
        group_name = sg_value.get("GroupName")
        vpc_id = sg_value.get("VpcId")
        node_id = f"{account_id}:{region}:{node_type}:{group_id}"
        name_tag = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), None)
        main = (group_name == "default")

        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": group_id,
            "name": name_tag or group_name or group_id,
            "main": main,
            "vpc_id": vpc_id,
            "attributes": {
                "description": sg_value.get("Description"),
                "inbound_rules_count": len(sg_value.get("IpPermissions", [])),
                "outbound_rules_count": len(sg_value.get("IpPermissionsEgress", [])),
                "inbound_rules": sg_value.get("IpPermissions", []),
                "outbound_rules": sg_value.get("IpPermissionsEgress", [])
            }
        }
        nodes.append(node)
    
    return nodes
