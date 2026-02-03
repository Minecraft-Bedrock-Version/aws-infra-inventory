from __future__ import annotations
from typing import Any, Dict
from datetime import timezone

def normalize_ec2(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    #Node 생성
    instances = raw_payload.get("instances", [])
    nodes = []
    for instance_value in instances:
        instance_id = instance_value.get("InstanceId")
        tags = instance_value.get("Tags", [])
        network_interfaces = instance_value.get("NetworkInterfaces", [])
        
        #각 필드를 채우기 위한 값
        node_type = "ec2_instance"
        node_id = f"{account_id}:{region}:ec2:{instance_id}"
        #resoucre id == instance id
        name = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), None)
        instance_type = instance_value.get("InstanceType")
        state = instance_value.get("State").get("Name")
        public_ip = instance_value.get("PublicIpAddress")
        private_ip = instance_value.get("PrivateIpAddress")
        launch_time = _iso(instance_value.get("LaunchTime"))
        vpc_id = instance_value.get("VpcId")
        subnet_id = instance_value.get("SubnetId")
        key_name = instance_value.get("KeyName")
        instance_profile = (instance_value.get("IamInstanceProfile") or {}).get("Arn")
        security_group = network_interfaces[0].get("Groups", [])

        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": instance_id,
            "name": name,
            "account_id": account_id,
            "region": region,
            "attributes": {
                "instance_type": instance_type,
                "state": state,
                "public": public_ip is not None,
                "public_ip": public_ip,
                "private_ip": private_ip,
                "launch_time": launch_time,
                "vpc_id": vpc_id,
                "subnet_id": subnet_id,
                "key_name": key_name,
                "iam_instance_profile": instance_profile,
                "security_groups": security_group
            }
        }
        nodes.append(node)
    
    return nodes

def _iso(dt_obj: Any) -> str | None: #json 처리를 위한 str 변환 및 시간 표준화
    if dt_obj is None: return None
    try:
        return dt_obj.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception: return str(dt_obj)