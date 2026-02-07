from __future__ import annotations
from typing import Any, Dict
import re

SQS_PATTERN = r"(https://sqs\.[a-z0-9-]+\.amazonaws\.com/[^\s'\"]+)"
RDS_PATTERN = r"[^\s'\"/]+\.([a-z0-9-]+)\.rds\.amazonaws\.com"

def graph_ec2(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    
    instances = raw_payload.get("ec2", {}).get("instances", [])
    #Edge 생성
    edges = []
    seen_edges = set() #edge 중복 생성을 막기위한 set
    
    for instance_value in instances: #raw data에서 인스턴스를 하나씩 조회
        instance_id = instance_value.get("InstanceId")
        node_id = f"{account_id}:{region}:ec2:{instance_id}"
                       
        public_ip = instance_value.get("PublicIpAddress") #public ip 읽어옴

        if public_ip: #인스턴스에 public ip가 존재한다면
            instance_subnet = instance_value.get("SubnetId") #인스턴스의 서브넷을 불러오고,
            route_tables = raw_payload.get("route_table", {}).get("RouteTables", []) #라우트 테이블 raw data도 불러와서
            for route_table in route_tables: #라우트 테이블 목록 순회
                associations = route_table.get("Associations", []) 
                associated = False #Associations 내부에 subnet id가 잇는지 확인
                for assoc in associations: #Associations 순회
                    if assoc.get("SubnetId") == instance_subnet: #인스턴스와 일치하는 서브넷 id가 있으면
                        associated = True #true로 변경
                if not associated: #순회 다 했는데 False 그대로면 종료
                    continue
                for route in route_table.get("Routes", []): #True 값이면 해당 라우트 테이블의 Associations 내부 Routes 목록 순회하며
                    gateway_id = route.get("GatewayId") #igw id와 
                    destination = route.get("DestinationCidrBlock") #cidr 블록을 꺼내옴
                    #만약 igw가 존재하고, cidr 블록이 모든 ip 대역으로 열려있으면 (public) edge 생성
                    if gateway_id and destination == "0.0.0.0/0":
                        igw_node_id = f"{account_id}:{region}:igw:{gateway_id}"
                        edge_id = f"edge:{instance_id}:EC2_ACCESS_IGW:{gateway_id}"
                        if edge_id not in seen_edges:
                            seen_edges.add(edge_id)
                            edges.append({
                                "id": edge_id,
                                "relation": "EC2_PUBLIC",
                                "src": node_id,
                                "dst": igw_node_id,
                                "directed": False,
                                "conditions": "EC2 is assigned a public IP, and the subnet where EC2 is located is connected to an IGW that can communicate externally through the route table."
                            })

        user_data = instance_value.get("UserData", "") #user data 읽어옴
        
        for match in re.findall(SQS_PATTERN, user_data): #sqs url이 userdata에 포함되어 있는지 확인
            queues = raw_payload.get("sqs", {}).get("queues", []) #찾는다면 sqs raw data에서
            for queue in queues: #queue를 모두 읽음
                queue_url = queue.get("QueueUrl", "")
                attributes = queue.get("Attributes", {})
                attribure_arn = attributes.get("QueueArn")
                name = attribure_arn.split(':')[-1]
                if match in queue_url: #user data에 포함된 q url이랑 일치하는 url을 지녔다면
                    edge_id = f"edge:{instance_id}:EC2_ACCESS_SQS:{name}" #edge id 미리 생성 (중복 방지)
                    if edge_id not in seen_edges: #edgeid가 seen_edges에 포함되어있지 않으면
                        seen_edges.add(edge_id) #해당 edge id를 seen edges에 넣고,
                        sqs_node_id = f"{account_id}:{region}:sqs:{name}" #sqs node id를 정의된 형식에 맞게 생성하여
                        edges.append({ #edges에 edge 추가
                            "id": edge_id,
                            "relation": "EC2_ACCESS_SQS",
                            "src": node_id,
                            "dst": sqs_node_id,
                            "directed": True,
                            "conditions": "The user data for the EC2 instance contains the URL of the SQS queue. You can call SQS from EC2. For more information, see Roles Associated with EC2."
                        })
                    
        for match in re.findall(RDS_PATTERN, user_data): #rds endpoint가 userdata에 포함되어 있는지 확인
            rds_instances = raw_payload.get("rds", {}).get("instances", [])  #찾는다면 rds raw data에서
            for rds in rds_instances: #instance를 모두 읽음
                rds_id = rds.get("DBInstanceIdentifier", "")
                endpoint = rds.get("Endpoint", {}).get("Address", "")
                if match in endpoint: #user data에 포함된 endpoint랑 일치하는 endpoint를 지녔다면
                    edge_id = f"edge:{instance_id}:EC2_ACCESS_RDS:{rds_id}" #edge id 미리 생성 (중복 방지)
                    if edge_id not in seen_edges: #edgeid가 seen_edges에 포함되어있지 않으면
                        seen_edges.add(edge_id) #해당 edge id를 seen edges에 넣고,
                        rds_node_id = f"{account_id}:{region}:rds:{rds_id}" #rds node id를 정의된 형식에 맞게 생성하여
                        edges.append({ #edges에 edge 추가
                            "id": edge_id,
                            "relation": "EC2_ACCESS_RDS",
                            "src": node_id,
                            "dst": rds_node_id,
                            "directed": False,
                            "conditions": "The user data for the EC2 instance contains the endpoint of the RDS. You can access RDS from EC2. For more information, see Roles Associated with EC2."
                        })
                        
    return edges
