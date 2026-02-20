from __future__ import annotations
from typing import Any, Dict
from datetime import timezone
import re 

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
        node_id = f"{account_id}:{region}:ec2_instance:{instance_id}"
        name = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), None)
        instance_type = instance_value.get("InstanceType")
        state = instance_value.get("State").get("Name")
        public_ip = instance_value.get("PublicIpAddress")
        private_ip = instance_value.get("PrivateIpAddress")
        launch_time = _iso(instance_value.get("LaunchTime"))
        vpc_id = instance_value.get("VpcId")
        subnet_id = instance_value.get("SubnetId")
        key_name = instance_value.get("KeyName")
        #(수정) instance profile 이름만 추출하도록 
        instance_profile_arn = (instance_value.get("IamInstanceProfile") or {}).get("Arn") #instance profile 수집
        instance_profile = instance_profile_arn.split('/')[-1] if instance_profile_arn else None #instance profile arn에서 이름만 추출
        network_interfaces = instance_value.get("NetworkInterfaces", []) #ec2에 연결된 네트워크 인터페이스 목록 가져옴

        security_groups = [ #보안 그룹 수집
            sg
            for nic in network_interfaces
            for sg in nic.get("Groups", [])
        ]

        #(수정) 필드 추가
        imds_token = (instance_value.get("MetadataOptions") or {}).get("HttpTokens") #IMDSv2 토큰 설정 추출
        ecs_cluster = (instance_value.get("EcsClusterName"))
        

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
                "security_groups": security_groups,
                #(수정) 새 필드 추가
                "imds_token": imds_token,
                "ecs_cluster": ecs_cluster,
                "tags": tags
            }
        }
        nodes.append(node)
    
    return nodes
