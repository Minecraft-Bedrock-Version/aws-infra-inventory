from __future__ import annotations
from typing import Any, Dict
import re

def graph_user(raw_payload: Dict[str, Any], account_id: str, region: str, node=None) -> Dict[str, Any]:
    #Edge 생성
    edges = []
    seen_edges = set() #edge 중복 생성을 막기위한 set
    
    if node: #만약 cli node가 따로 넘어왔다면
        node_type = node.get("node_type") #node type 추출
        name = node.get("resource_id") #resource id 추출
        node_id = node.get("node_id") #node id 추출

        attrs = node.get("attributes", {}) #속성값 추출
        policies = [] #정책 리스트에
        policies.extend(attrs.get("attached_policies", [])) #관리형 정책,
        policies.extend(attrs.get("inline_policies", [])) #인라인 정책 추가
        users = [] #users 리스트는 빈 값
        
    else:
        users = raw_payload.get("iam_user", {}).get("users", []) #cli node가 따로 안넘어왔으면 users를 raw data로 저장해두기
        
    target_users = list(users) #edge 만들 때 사용되는 target users 리스트에 기존 raw data를 넣어두고,
    
    if node: #cli node가 있다면
        target_users.append({ #해당 node의 특정 속성을 추가하기
            "UserName": name,
            "AttachedPolicies": attrs.get("attached_policies", []),
            "InlinePolicies": attrs.get("inline_policies", [])
        })
    
    #현재 구현된 서비스들의 node들 모두 미리 불러와두기
    sqs_nodes = raw_payload.get("sqs", {}).get("queues", [])
    ec2_nodes = raw_payload.get("ec2", {}).get("instances", [])
    iam_roles = raw_payload.get("iam_role", {}).get("roles", [])
    rds_nodes = raw_payload.get("rds", {}).get("instances", [])
    lambda_nodes = raw_payload.get("lambda", {}).get("functions", [])

    for user_value in target_users: #User 목록 순회
        node_type = "iam_user"
        name = user_value.get("UserName")
        node_id = f"{account_id}:{node_type}:{name}"
        
        policies = [] #해당 리스트에
        policies.extend(user_value.get("AttachedPolicies", [])) #관리형 정책과
        policies.extend(user_value.get("InlinePolicies", [])) #인라인 정책 추가
        
        for policy in policies: #정책들 순회
            doc = policy.get("PolicyDocument") or policy.get("Document") or {"Statement": policy.get("Statement", [])} #정책의 내용만 조회
            if not doc: #정책이 비어있으면 종료
                continue
            for stmt in doc.get("Statement", []): #버전 제외 정책의 권한 목록 조회
                if stmt.get("Effect") != "Allow": #허용 정책이 아니라 거부 정책이면 제외
                    continue
                actions = stmt.get("Action", []) #action과 
                resources = stmt.get("Resource", []) #resource 조회
                if isinstance(actions, str):
                    actions = [actions]
                if isinstance(resources, str):
                    resources = [resources]
                for action in actions: #action을 순회하며
                    service = action.split(":")[0] #세미콜론을 기준으로 앞쪽의 서비스를 가져옴
                    
###################################################################################################################
############################################### Resource가 * 라면 ###################################################
###################################################################################################################

                    if "*" in resources: #해당 action이 포함된 문서의 recource가 * 이라면 각 서비스의 모든 노드와 연결
                        #SQS 모든 node와 연결
                        if service == "sqs": #서비스가 sqs라면
                            for q in sqs_nodes: #sqs 모든 노드를 순회하며
                                qname = q["Attributes"]["QueueArn"].split(":")[-1] #id 생성에 필요한 name 추출
                                dst = f"{account_id}:{region}:sqs:{qname}" #sqs node id 구성
                                edge_id = f"edge:{name}:IAM_USER_ACCESS_SQS:{qname}" #edge id 구성
                                if edge_id not in seen_edges: #중복 방지를 위해 seen_edges 확인 후
                                    seen_edges.add(edge_id)
                                    edges.append({ #edge 생성
                                        "id": edge_id,
                                        "relation": "IAM_USER_ACCESS_SQS",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User has access to SQS."
                                    })
                        #EC2 모든 노드와 연결
                        if service == "ec2":
                            for inst in ec2_nodes:
                                iid = inst["InstanceId"]
                                dst = f"{account_id}:{region}:ec2:{iid}"
                                edge_id = f"edge:{name}:IAM_USER_ACCESS_EC2:{iid}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_USER_ACCESS_EC2",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User has access to EC2."
                                    })
                        #IAM 모든 노드 연결
                        if service == "iam":
                            action_name = action.split(":")[1] if ":" in action else ""
                            if action_name.lower().startswith("get") or action_name.lower().startswith("list"):
                                continue
                            #모든 role과 연결
                            for role in iam_roles:
                                role_name = role["RoleName"]
                                dst = f"{account_id}:iam_role:{role_name}"
                                edge_id = f"edge:{name}:IAM_USER_ACCESS_IAM:{role_name}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_USER_ACCESS_IAM",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User has access to IAM."
                                    })
                            #모든 user와 연결
                            for user in users:
                                if user == user_value: #현재 user (본인) 제외
                                    continue
                                user_name = user["UserName"]
                                dst = f"{account_id}:iam_user:{user_name}"
                                edge_id = f"edge:{name}:IAM_USER_ACCESS_IAM:{user_name}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_USER_ACCESS_IAM",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User has access to IAM."
                                    })
                        #RDS 모든 노드와 연결
                        if service == "rds":
                            for inst in rds_nodes:
                                iid = inst["DBInstanceIdentifier"]
                                dst = f"{account_id}:{region}:rds:{iid}"
                                edge_id = f"edge:{name}:IAM_USER_ACCESS_RDS:{iid}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_USER_ACCESS_RDS",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User has access to RDS."
                                    })
                        #Lambda 모든 노드와 연결
                        if service == "lambda":
                            for func in lambda_nodes:
                                fname = func["FunctionName"]
                                dst = f"{account_id}:{region}:lambda:{fname}"
                                edge_id = f"edge:{name}:IAM_USER_ACCESS_LAMBDA:{fname}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_USER_ACCESS_LAMBDA",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User has access to Lambda."
                                    })
                        if service == "sts": #서비스가 sts라면
                            for role in iam_roles:
                                role_name = role["RoleName"]
                                dst = f"{account_id}:iam_role:{role_name}"
                                edge_id = f"edge:{name}:IAM_USER_ASSUME_ROLE:{role_name}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_USER_ASSUME_ROLE",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User can Assume ANY IAM Role."
                                    })
                                    
###################################################################################################################
############################################ Resource가 * 아니라면 ###################################################
###################################################################################################################

                    else:
                        for res in resources:
                            #AssumeRole 경우
                            if service == "sts" and ":role/" in res: #서비스가 sts이고 resource에 role이 포함되어 있으면
                                role_name = res.split("/")[-1] #role 이름을 추출
                                dst = f"{account_id}:iam_role:{role_name}" 
                                edge_id = f"edge:{name}:IAM_USER_ASSUME_ROLE:{role_name}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_USER_ASSUME_ROLE",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User can Assume Roles."
                                    })
                            #특정 role 대상인 경우 해당 role과 연결
                            if service == "iam" and ":role/" in res: #서비스가 iam이고 resource에 role이 포함되어 있으면
                                role_name = res.split("/")[-1] #role 이름을 추출
                                dst = f"{account_id}:iam_role:{role_name}" 
                                edge_id = f"edge:{name}:IAM_USER_ACCESS_ROLE:{role_name}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_USER_ACCESS_ROLE",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User has access to IAM Role."
                                    })
                            #특정 user 대상인 경우 해당 user와 연결
                            if service == "iam" and ":user/" in res: #서비스가 iam이고 resource에 user가 포함되어 있으면
                                user_name = res.split("/")[-1] #user 이름을 추출
                                dst = f"{account_id}:iam_user:{user_name}" 
                                edge_id = f"edge:{name}:IAM_USER_ACCESS_USER:{user_name}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_USER_ACCESS_USER",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User has access to IAM User."
                                    })
                            #특정 sqs 대상인 경우 해당 sqs와 연결
                            if service == "sqs" and ":sqs:" in res: #서비스가 sqs이고 resource에 sqs가 포함되어 있으면
                                qname = res.split(":")[-1] #sqs 이름 추출
                                dst = f"{account_id}:{region}:sqs:{qname}"
                                edge_id = f"edge:{name}:IAM_USER_ACCESS_SQS:{qname}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_USER_ACCESS_SQS",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User has access to SQS Queue."
                                    })
                            #특정 ec2 인스턴스 대상인 경우 해당 ec2 인스턴스와 연결
                            if service == "ec2" and ":ec2:" in res and ":instance/" in res: #서비스가 ec2이고 resource에 ec2 및 :instance/가 포함되어 있으면
                                iid = res.split("/")[-1] #인스턴스 id 추출
                                dst = f"{account_id}:{region}:ec2:{iid}"
                                edge_id = f"edge:{name}:IAM_USER_ACCESS_EC2:{iid}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_USER_ACCESS_EC2",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User has access to EC2 Instance."
                                    })   
                            #특정 rds 인스턴스 대상인 경우 해당 rds 인스턴스와 연결
                            if service == "rds" and ":rds:" in res and ":db/" in res: #서비스가 rds이고 resource에 rds 및 :db/가 포함되어 있으면
                                db_name = res.split("/")[-1] #DB name 추출
                                for inst in rds_nodes: #rds node들 순회하면서
                                    rds_name = inst["DBName"] #DB name이
                                    if rds_name == db_name: #추출된 dbname과 같다면 edge 추가
                                        rds_id = inst["DBInstanceIdentifier"]
                                        dst = f"{account_id}:{region}:rds:{rds_id}"
                                        edge_id = f"edge:{name}:IAM_USER_ACCESS_RDS:{rds_id}"
                                        if edge_id not in seen_edges:
                                            seen_edges.add(edge_id)
                                            edges.append({
                                                "id": edge_id,
                                                "relation": "IAM_USER_ACCESS_RDS",
                                                "src": node_id,
                                                "dst": dst,
                                                "directed": True,
                                                "conditions": "This User has access to RDS Instance."
                                            })   
                            #특정 Lambda 함수 대상인 경우 해당 Lambda 함수와 연결                    
                            if service == "lambda" and ":lambda:" in res and ":function/" in res: #서비스가 lambda이고 resource에 lambda 및 :function/이 포함되어 있으면
                                fname = res.split("/")[-1] #Lambda 이름 추출
                                dst = f"{account_id}:{region}:lambda:{fname}"
                                edge_id = f"edge:{name}:IAM_USER_ACCESS_LAMBDA:{fname}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_USER_ACCESS_LAMBDA",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This User has access to Lambda Function."
                                    })                        

    return edges
