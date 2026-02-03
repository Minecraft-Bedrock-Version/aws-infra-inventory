from __future__ import annotations
from typing import Any, Dict, List
import re

#EC2 IP가 존재하는지 확인하기 위해 ip 패턴 정의
IP_PATTERN = r"\b\d{1,3}(?:\.\d{1,3}){3}\b"

def graph_lambda(raw_payload: Dict[str, Any], account_id: str, region: str, node=None) -> Dict[str, Any]:
    #Edge 생성
    functions = raw_payload.get("lambda", {}).get("functions", [])
    edges = []
    seen_edges = set() #edge 중복 생성을 막기위한 set
    
    ec2_instances = raw_payload.get("ec2", {}).get("instances", []) #raw data의 EC2 목록 불러오기 -> Lambda 환경 변수에 EC2 Ip 존재 여부 확인용

    for function_value in functions: #Lambda 함수 순회
        node_type = "lambda"
        name = function_value.get("FunctionName")
        node_id = f"{account_id}:{region}:{node_type}:{name}"
        
        env_vars = function_value.get("Environment", {}).get("Variables", {}) #Lambda 환경 변수 불러오기
        env_text = " ".join(env_vars.values()) #한 줄의 문자열로 만들어서 re.findall로 매칭 할 수 있는 형태로 만들기
        found_ips = re.findall(IP_PATTERN, env_text) #IP 형태의 변수가 존재하는지 확인
        for instance in ec2_instances: #인스턴스 목록 순회
            instance_id = instance.get("InstanceId")
            private_ip = instance.get("PrivateIpAddress")
            public_ip = instance.get("PublicIpAddress")
            ec2_node_id = f"{account_id}:{region}:ec2:{instance_id}"
            for ip in found_ips: #변수에서 발견한 IP를 순회
                if ip == private_ip or ip == public_ip: #해당 IP가 EC2의 private 또는 public ip와 일치한다면
                    edge_id = f"edge:{name}:LAMBDA_CALL_EC2:{instance_id}"
                    #Edge 생성
                    if edge_id not in seen_edges:
                        seen_edges.add(edge_id)
                        edges.append({
                            "id": edge_id,
                            "relation": "LAMBDA_CALL_EC2",
                            "src": node_id,
                            "dst": ec2_node_id,
                            "directed": True,
                            "conditions": "This Lambda function's environment variables contain an EC2 public or private IP address. EC2 is accessible. For more information, check the role associated with the Lambda function."
                        })
                        
                        
        mappings = function_value.get("EventSourceMappings", []) #Event Source Mapping 안의 내용을 불러와서
        for mapping in mappings: #순회
            event_source_arn = mapping.get("EventSourceArn", "") #Event Source Arn을 불러옴
            if event_source_arn.startswith("arn:aws:sqs"): #해당 arn의 시작이 sqs라면
                queue_name = event_source_arn.split(":")[-1] #세미콜론을 기준으로 sqs의 이름만 가져옴
                sqs_node_id = f"{account_id}:{region}:sqs:{queue_name}" #sqs nodeid 정의
                edges.append({
                    "id": f"edge:{queue_name}:SQS_TRIGGER_LAMBDA:{name}",
                    "relation": "SQS_TRIGGER_LAMBDA",
                    "src": sqs_node_id,
                    "dst": node_id,
                    "directed": True,
                    "conditions": "I found the SQS Queue ARN in the Event Source Mapping of this Lambda function."
                })

    return edges
