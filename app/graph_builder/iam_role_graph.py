from __future__ import annotations
from typing import Any, Dict
import re

def graph_role(raw_payload: Dict[str, Any], account_id: str, region: str, node=None) -> Dict[str, Any]:
    #Edge 생성
    roles = raw_payload.get("iam_role", {}).get("roles", [])
    edges = []
    seen_edges = set() #edge 중복 생성을 막기위한 set
    
    #현재 구현된 서비스들의 node들 모두 미리 불러와두기
    sqs_nodes = raw_payload.get("sqs", {}).get("queues", [])
    ec2_nodes = raw_payload.get("ec2", {}).get("instances", [])
    iam_users = raw_payload.get("iam_user", {}).get("users", [])
    rds_nodes = raw_payload.get("rds", {}).get("instances", [])
    lambda_nodes = raw_payload.get("lambda", {}).get("functions", [])

    for role_value in roles: #User 목록 순회
        node_type = "iam_role"
        name = role_value.get("RoleName")
        node_id = f"{account_id}:{node_type}:{name}"
        
        assume_doc = role_value.get("AssumeRolePolicyDocument", {}) #Assume 대상 문서
        for stmt in assume_doc.get("Statement", []): #Statement 순회하며
            if stmt.get("Effect") != "Allow": #거부라면 종료
                continue
            principal = stmt.get("Principal", {}) #대상 조건 불러와서
            service_principal = principal.get("Service") #서비스 필드 불러오기
            if service_principal: #서비스 필드가 존재하면
                if isinstance(service_principal, str):
                    service_principal = [service_principal]
                for sp in service_principal: #순회하며
                    svc = sp.split(".")[0] #url 형식 중에서 서비스만 가져옴
                    if svc == "lambda": #해당 서비스가 Lambda라면
                        for func in lambda_nodes: #모든 람다 노드를 순회하여 연결
                            fname = func["FunctionName"]
                            src = f"{account_id}:{region}:lambda:{fname}"
                            dst = node_id
                            edge_id = f"edge:{fname}:ASSUME_ROLE:{name}"
                            if edge_id not in seen_edges:
                                seen_edges.add(edge_id)
                                edges.append({
                                    "id": edge_id,
                                    "relation": "ASSUME_ROLE",
                                    "src": src,
                                    "dst": dst,
                                    "directed": True,
                                    "conditions": "A role that a Lambda function can assume."
                                })
                    if svc == "ec2": #해당 서비스가 ec2라면
                        for inst in ec2_nodes: #모든 ec2 노드를 순회하여 연결
                            iid = inst["InstanceId"]
                            src = f"{account_id}:{region}:ec2:{iid}"
                            dst = node_id
                            edge_id = f"edge:{iid}:ASSUME_ROLE:{name}"
                            if edge_id not in seen_edges:
                                seen_edges.add(edge_id)
                                edges.append({
                                    "id": edge_id,
                                    "relation": "ASSUME_ROLE",
                                    "src": src,
                                    "dst": dst,
                                    "directed": True,
                                    "conditions": "A role that a EC2 Instance can assume."
                                })
                    if svc == "rds": #해당 서비스가 rds라면
                        for inst in rds_nodes: #모든 rds 노드를 순회하여 연결
                            iid = inst["DBInstanceIdentifier"]
                            src = f"{account_id}:{region}:rds:{iid}"
                            dst = node_id
                            edge_id = f"edge:{iid}:ASSUME_ROLE:{name}"
                            if edge_id not in seen_edges:
                                seen_edges.add(edge_id)
                                edges.append({
                                    "id": edge_id,
                                    "relation": "ASSUME_ROLE",
                                    "src": src,
                                    "dst": dst,
                                    "directed": True,
                                    "conditions": "A role that a RDS Instance can assume."
                                })
                                
            aws_principal = principal.get("AWS") #AWS 필드 불러오기
            if aws_principal: #AWS 필드가 존재하면
                if isinstance(aws_principal, str):
                    aws_principal = [aws_principal]
                for ap in aws_principal: #순회하며
                    if ":user/" in ap: #대상이 User 라면
                        user_name = ap.split("/")[-1] #User 이름을 가져와서 edge 생성
                        src = f"{account_id}:iam_user:{user_name}"
                        dst = node_id
                        edge_id = f"edge:{user_name}:ASSUME_ROLE:{name}"
                        if edge_id not in seen_edges:
                            seen_edges.add(edge_id)
                            edges.append({
                                "id": edge_id,
                                "relation": "ASSUME_ROLE",
                                "src": src,
                                "dst": dst,
                                "directed": True,
                                "conditions": "This is a role that an IAM User can assume."
                            })
                    if ":role/" in ap: #대상이 역할이라면
                        role_name = ap.split("/")[-1] #역할 이름을 가져와서 edge 생성
                        src = f"{account_id}:iam_role:{role_name}"
                        dst = node_id
                        edge_id = f"edge:{role_name}:ASSUME_ROLE:{name}"
                        if edge_id not in seen_edges:
                            seen_edges.add(edge_id)
                            edges.append({
                                "id": edge_id,
                                "relation": "ASSUME_ROLE",
                                "src": src,
                                "dst": dst,
                                "directed": True,
                                "conditions": "This is a role that an IAM Role can assume."
                            })
                            
        policies = [] #해당 리스트에
        policies.extend(role_value.get("AttachedPolicies", [])) #관리형 정책과
        policies.extend(role_value.get("InlinePolicies", [])) #인라인 정책 추가
        
        for policy in policies: #정책들 순회
            if "Versions" in policy: #관리형 정책의 경우 Version의 DefaultVersion 가져오기
                docs = [v["Document"] for v in policy.get("Versions", []) if v.get("IsDefaultVersion")]
            elif "PolicyDocument" in policy: #인라인 정책의 경우 정책 내용 가져오기
                docs = [policy["PolicyDocument"]]
            else:
                continue

            for doc in docs:                        
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
                                edge_id = f"edge:{name}:IAM_ROLE_ACCESS_SQS:{qname}" #edge id 구성
                                if edge_id not in seen_edges: #중복 방지를 위해 seen_edges 확인 후
                                    seen_edges.add(edge_id)
                                    edges.append({ #edge 생성
                                        "id": edge_id,
                                        "relation": "IAM_ROLE_ACCESS_SQS",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This role gives you access to SQS."
                                    })
                        #EC2 모든 노드와 연결
                        if service == "ec2":
                            for inst in ec2_nodes:
                                iid = inst["InstanceId"]
                                dst = f"{account_id}:{region}:ec2:{iid}"
                                edge_id = f"edge:{name}:IAM_ROLE_ACCESS_EC2:{iid}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_ROLE_ACCESS_EC2",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This role gives you access to EC2."
                                    })
                        #IAM 모든 노드 연결
                        if service == "iam":
                            #모든 user와 연결
                            for user in iam_users:
                                user_name = user["UserName"]
                                dst = f"{account_id}:iam_user:{user_name}"
                                edge_id = f"edge:{name}:IAM_ROLE_ACCESS_IAM:{user_name}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_ROLE_ACCESS_IAM",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This role gives you access to IAM."
                                    })
                            #모든 role과 연결
                            for role in roles:
                                if role == role_value: #현재 role 제외
                                    continue
                                role_name = role["RoleName"]
                                dst = f"{account_id}:iam_role:{role_name}"
                                edge_id = f"edge:{name}:IAM_ROLE_ACCESS_IAM:{role_name}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_ROLE_ACCESS_IAM",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This role gives you access to IAM."
                                    })
                        #RDS 모든 노드와 연결
                        if service == "rds":
                            for inst in rds_nodes:
                                iid = inst["DBInstanceIdentifier"]
                                dst = f"{account_id}:{region}:rds:{iid}"
                                edge_id = f"edge:{name}:IAM_ROLE_ACCESS_RDS:{iid}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_ROLE_ACCESS_RDS",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This role gives you access to RDS."
                                    })
                        #Lambda 모든 노드와 연결
                        if service == "lambda":
                            for func in lambda_nodes:
                                fname = func["FunctionName"]
                                dst = f"{account_id}:{region}:lambda:{fname}"
                                edge_id = f"edge:{name}:IAM_ROLE_ACCESS_LAMBDA:{fname}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_ROLE_ACCESS_LAMBDA",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This role gives you access to Lambda."
                                    })
                                    
###################################################################################################################
############################################ Resource가 * 아니라면 ###################################################
###################################################################################################################

                    else:
                        for res in resources:
                            #특정 user 대상인 경우 해당 user와 연결
                            if service == "iam" and ":user/" in res: #서비스가 iam이고 resource에 user가 포함되어 있으면
                                user_name = res.split("/")[-1] #user 이름을 추출
                                dst = f"{account_id}:iam_user:{user_name}" 
                                edge_id = f"edge:{name}:IAM_ROLE_ACCESS_USER:{user_name}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_ROLE_ACCESS_USER",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This role gives you access to IAM User."
                                    })
                            #특정 role 대상인 경우 해당 role과 연결
                            if service == "iam" and ":role/" in res: #서비스가 iam이고 resource에 role이 포함되어 있으면
                                role_name = res.split("/")[-1] #role 이름을 추출
                                dst = f"{account_id}:iam_role:{role_name}" 
                                edge_id = f"edge:{name}:IAM_ROLE_ACCESS_ROLE:{role_name}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_ROLE_ACCESS_ROLE",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This role gives you access to IAM Role."
                                    })
                            #특정 sqs 대상인 경우 해당 sqs와 연결
                            if service == "sqs" and ":sqs:" in res: #서비스가 sqs이고 resource에 sqs가 포함되어 있으면
                                qname = res.split(":")[-1] #sqs 이름 추출
                                dst = f"{account_id}:{region}:sqs:{qname}"
                                edge_id = f"edge:{name}:IAM_ROLE_ACCESS_SQS:{qname}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_ROLE_ACCESS_SQS",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This role gives you access to SQS Queue."
                                    })
                            #특정 ec2 인스턴스 대상인 경우 해당 ec2 인스턴스와 연결
                            if service == "ec2" and ":ec2:" in res and ":instance/" in res: #서비스가 ec2이고 resource에 ec2 및 :instance/가 포함되어 있으면
                                iid = res.split("/")[-1] #인스턴스 id 추출
                                dst = f"{account_id}:{region}:ec2:{iid}"
                                edge_id = f"edge:{name}:IAM_ROLE_ACCESS_EC2:{iid}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_ROLE_ACCESS_EC2",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This role gives you access to EC2 Instance."
                                    })   
                            #특정 rds 인스턴스 대상인 경우 해당 rds 인스턴스와 연결
                            if service == "rds" and ":rds:" in res and ":db/" in res: #서비스가 rds이고 resource에 rds 및 :db/가 포함되어 있으면
                                db_name = res.split("/")[-1] #DB name 추출
                                for inst in rds_nodes: #rds node들 순회하면서
                                    rds_name = inst["DBName"] #DB name이
                                    if rds_name == db_name: #추출된 dbname과 같다면 edge 추가
                                        rds_id = inst["DBInstanceIdentifier"]
                                        dst = f"{account_id}:{region}:rds:{rds_id}"
                                        edge_id = f"edge:{name}:IAM_ROLE_ACCESS_RDS:{rds_id}"
                                        if edge_id not in seen_edges:
                                            seen_edges.add(edge_id)
                                            edges.append({
                                                "id": edge_id,
                                                "relation": "IAM_ROLE_ACCESS_RDS",
                                                "src": node_id,
                                                "dst": dst,
                                                "directed": True,
                                                "conditions": "This role gives you access to RDS Instance."
                                            })   
                            #특정 Lambda 함수 대상인 경우 해당 Lambda 함수와 연결                    
                            if service == "lambda" and ":lambda:" in res and ":function/" in res: #서비스가 lambda이고 resource에 lambda 및 :function/이 포함되어 있으면
                                fname = res.split("/")[-1] #Lambda 이름 추출
                                dst = f"{account_id}:{region}:lambda:{fname}"
                                edge_id = f"edge:{name}:IAM_ROLE_ACCESS_LAMBDA:{fname}"
                                if edge_id not in seen_edges:
                                    seen_edges.add(edge_id)
                                    edges.append({
                                        "id": edge_id,
                                        "relation": "IAM_ROLE_ACCESS_LAMBDA",
                                        "src": node_id,
                                        "dst": dst,
                                        "directed": True,
                                        "conditions": "This role gives you access to Lambda Function."
                                    })                        

    return edges
