from __future__ import annotations
from typing import Any, Dict, List
import re

#EC2 IP가 존재하는지 확인하기 위해 ip 패턴 정의
IP_PATTERN = r"\b\d{1,3}(?:\.\d{1,3}){3}\b"

def graph_lambda(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    # Lambda 설정/환경변수/EventSourceMapping 기반으로 관계(edge) 생성
    functions = raw_payload.get("lambda", {}).get("functions", [])
    edges = []
    # seen_edges: (src, relation, dst) 조합이 동일한 edge가 여러 번 생성되는 것을 방지하기 위한 캐시
    # - Lambda 환경변수/IP 매칭, EventSourceMapping 등을 순회하다 보면 같은 관계가 중복으로 발견될 수 있음
    # - edge_id를 키로 dedup 하여 그래프를 안정적으로 유지
    seen_edges = set()

    # _add_edge: edge 생성 규칙을 한 곳으로 모아 포맷/중복 제거를 일관되게 처리하는 헬퍼
    # - relation, src, dst, conditions 필드를 공통 포맷으로 저장
    # - edge_id 기반으로 중복 생성 방지(dedup)
    # - 팀 내 graph 코드 규격(A+ 단계) 통일을 위해 추가됨
    def _add_edge(edge_id: str, relation: str, src: str, dst: str, conditions: str) -> None:
        if edge_id in seen_edges:
            return
        seen_edges.add(edge_id)
        edges.append({
            "id": edge_id,
            "relation": relation,
            "src": src,
            "dst": dst,
            "directed": True,
            "conditions": conditions,
        })
    
    ec2_instances = raw_payload.get("ec2", {}).get("instances", []) #raw data의 EC2 목록 불러오기 -> Lambda 환경 변수에 EC2 Ip 존재 여부 확인용

    for function_value in functions: #Lambda 함수 순회
        node_type = "lambda"
        name = function_value.get("FunctionName")
        node_id = f"{account_id}:{region}:{node_type}:{name}"
        
        # Lambda 실행 역할(Role) 연결: Lambda 설정에 지정된 Role ARN을 IAM Role 노드로 매핑
        role_arn = function_value.get("Role") or function_value.get("RoleArn")
        if role_arn and ":role/" in role_arn:
            role_name = role_arn.split("/")[-1]
            dst_role_id = f"{account_id}:iam_role:{role_name}"
            edge_id = f"edge:{name}:LAMBDA_ASSUME_ROLE:{role_name}"
            _add_edge(edge_id, "LAMBDA_ASSUME_ROLE", node_id, dst_role_id, "This Lambda function is configured to assume the specified IAM Role.")

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
                    _add_edge(
                        edge_id,
                        "LAMBDA_CALL_EC2",
                        node_id,
                        ec2_node_id,
                        "This Lambda function's environment variables contain an EC2 public or private IP address. EC2 is accessible. For more information, check the role associated with the Lambda function."
                    )
                        
                        
        mappings = function_value.get("EventSourceMappings", []) #Event Source Mapping 안의 내용을 불러와서
        for mapping in mappings: #순회
            event_source_arn = mapping.get("EventSourceArn", "") #Event Source Arn을 불러옴
            if event_source_arn.startswith("arn:aws:sqs"): #해당 arn의 시작이 sqs라면
                queue_name = event_source_arn.split(":")[-1] #세미콜론을 기준으로 sqs의 이름만 가져옴
                sqs_node_id = f"{account_id}:{region}:sqs:{queue_name}" #sqs nodeid 정의
                edge_id = f"edge:{queue_name}:SQS_TRIGGER_LAMBDA:{name}"
                _add_edge(
                    edge_id,
                    "SQS_TRIGGER_LAMBDA",
                    sqs_node_id,
                    node_id,
                    "I found the SQS Queue ARN in the Event Source Mapping of this Lambda function."
                )

    return edges
