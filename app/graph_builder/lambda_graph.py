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
    
    # 서비스 node들 모두 미리 불러와두기
    ec2_instances = raw_payload.get("ec2", {}).get("instances", [])
    iam_users = raw_payload.get("iam", {}).get("users", [])
    iam_roles = raw_payload.get("iam", {}).get("roles", [])
    lambda_nodes = raw_payload.get("lambda", {}).get("functions", [])
    secrets = raw_payload.get("secretsmanager", {}).get("secrets", [])


    for function_value in functions: #Lambda 함수 순회
        node_type = "lambda"
        name = function_value.get("FunctionName")
        node_id = f"{account_id}:{region}:{node_type}:{name}"
        
        # (1) 람다가 환경 변수의 IP를 통해 EC2를 호출함 (LAMBDA_CALL_EC2)
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

        # (2) 추가: Lambda가 사용하는 IAM Role (LAMBDA_ASSUMES_ROLE)
        execution_role_arn = function_value.get("Role", "") 
        if execution_role_arn:
            role_name = execution_role_arn.split("/")[-1] # ARN에서 Role 이름 추출
            role_node_id = f"{account_id}:iam_role:{role_name}"
            role_edge_id = f"edge:{name}:ASSUMES_ROLE:{role_name}"
            
            if role_edge_id not in seen_edges:
                seen_edges.add(role_edge_id)
                edges.append({
                    "id": role_edge_id,
                    "relation": "LAMBDA_ASSUMES_ROLE",
                    "src": node_id,       # 출발지: Lambda Function
                    "dst": role_node_id,   # 목적지: IAM Role
                    "directed": True,
                    "conditions": f"This Lambda function executes with the permissions of {role_name} role."
                })
        
        # (3) Lambda의 실행 역할 상세 권한 분석
        for role in iam_roles: #iam role을 순회하면서
            if role.get("Arn") == execution_role_arn: # 현재 람다가 사용하는 역할 찾기
                inline_policies = role.get("InlinePolicies", []) #람다 역할에 정의된 인라인 정책 조회
                
                for policy in inline_policies: #인라인 정책 순회하면서
                    statements = policy.get("PolicyDocument", {}).get("Statement", []) #statement 조회
                    for stmt in statements: #statement 순회하면서
                        actions = stmt.get("Action", []) #action 조회
                        if isinstance(actions, str): actions = [actions] # Action이 단일 문자열일 경우 리스트로 변환

                        # (2-1) 권한 상승 위험이 있는 액션 정의
                        privilege_actions = ["iam:AttachUserPolicy", "iam:PutUserPolicy", "iam:AddUserToGroup"]
                        if any(act in actions for act in privilege_actions) or "*" in actions: #해당 액션이 포함되어 있거나, 모든 권한이 *인 경우
                            resources = stmt.get("Resource", []) #정책의 resource 필드 가져오기
                            if isinstance(resources, str): resources = [resources]
                            for res in resources:
                                target_user = None
                                if res == "*":
                                    target_user = "*" #모든 유저가 대상인 경우
                                elif "user/" in res:
                                    target_user = res.split("/")[-1] # 특정 유저가 대상인 경우 이름 추출
                                if target_user: #특정 유저 엣지 생성
                                    elevate_edge_id = f"edge:{name}:POLICY_CHANGE:{target_user}"
                                    if elevate_edge_id not in seen_edges:
                                        seen_edges.add(elevate_edge_id)
                                        edges.append({
                                            "id": elevate_edge_id,
                                            "relation": "POLICY_CHANGE", 
                                            "src": node_id, # 출발지: 권한을 가진 Lambda
                                            "dst": f"{account_id}:iam_user:{target_user}" if target_user != "*" else "ALL_USERS",
                                            "directed": True,
                                            "conditions": f"This Lambda can modify permissions for user '{target_user}'."
                                        })         

        # (4) SQS가 람다를 트리거함 (SQS_TRIGGER_LAMBDA)               
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
