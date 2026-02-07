from __future__ import annotations
from typing import Any, Dict

def graph_role(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    #Edge 생성
    roles = raw_payload.get("iam_role", {}).get("roles", [])
    edges = []
    # seen_edges: (src, relation, dst) 조합이 동일한 edge가 여러 번 생성되는 것을 방지하기 위한 캐시
    # - 정책 문서(Statement/Action/Resource)를 순회하다 보면 같은 관계가 중복으로 발견될 수 있음
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
    
    #현재 구현된 서비스들의 node들 모두 미리 불러와두기
    sqs_nodes = raw_payload.get("sqs", {}).get("queues", [])
    ec2_nodes = raw_payload.get("ec2", {}).get("instances", [])
    iam_users = raw_payload.get("iam_user", {}).get("users", [])
    rds_nodes = raw_payload.get("rds", {}).get("instances", [])
    lambda_nodes = raw_payload.get("lambda", {}).get("functions", [])
    secrets_nodes = raw_payload.get("secretsmanager", {}).get("secrets", [])

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
                            _add_edge(edge_id, "ASSUME_ROLE", src, dst, "A role that a Lambda function can assume.")
                    if svc == "ec2": #해당 서비스가 ec2라면
                        for inst in ec2_nodes: #모든 ec2 노드를 순회하여 연결
                            iid = inst["InstanceId"]
                            src = f"{account_id}:{region}:ec2:{iid}"
                            dst = node_id
                            edge_id = f"edge:{iid}:ASSUME_ROLE:{name}"
                            _add_edge(edge_id, "ASSUME_ROLE", src, dst, "A role that a EC2 Instance can assume.")
                    if svc == "rds": #해당 서비스가 rds라면
                        for inst in rds_nodes: #모든 rds 노드를 순회하여 연결
                            iid = inst["DBInstanceIdentifier"]
                            src = f"{account_id}:{region}:rds:{iid}"
                            dst = node_id
                            edge_id = f"edge:{iid}:ASSUME_ROLE:{name}"
                            _add_edge(edge_id, "ASSUME_ROLE", src, dst, "A role that a RDS Instance can assume.")
                                
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
                        _add_edge(edge_id, "ASSUME_ROLE", src, dst, "This is a role that an IAM User can assume.")
                    if ":role/" in ap: #대상이 역할이라면
                        role_name = ap.split("/")[-1] #역할 이름을 가져와서 edge 생성
                        src = f"{account_id}:iam_role:{role_name}"
                        dst = node_id
                        edge_id = f"edge:{role_name}:ASSUME_ROLE:{name}"
                        _add_edge(edge_id, "ASSUME_ROLE", src, dst, "This is a role that an IAM Role can assume.")
                            
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
                    # NOTE: Action 단위로 service를 결정하고, 그 Action에 대응하는 Resource 기준으로 edge를 생성해야 함
                    # - Action이 여러 개인 Statement에서 Resource 처리 로직이 바깥으로 빠지면 누락/오연결이 발생할 수 있음
                    # - 그래서 Resource 처리(if "*" in resources / else)는 반드시 이 Action 루프 내부에서 실행됨
                    for action in actions:  # action을 순회하며
                        service = action.split(":")[0]

                        # Lambda privesc-oriented relations (lambda_privesc 시나리오 분석용 추가 관계)
                        # - 기존 IAM_ROLE_ACCESS_* 는 "접근 가능" 수준의 범용 연결
                        # - 아래 3개는 권한 기반 "권한 상승/경로 분석"에 직접 쓰이는 신호(edge)로 별도 표기
                        #   1) iam:PassRole  -> 다른 Role을 Lambda 등에 전달 가능 (IAM_ROLE_CAN_PASS_ROLE)
                        #   2) sts:AssumeRole -> 다른 Role로 체인 Assume 가능 (IAM_ROLE_CAN_ASSUME_ROLE)
                        #   3) lambda:* 변경 권한 -> Lambda 코드/설정 변경으로 privesc 가능 (IAM_ROLE_CAN_MODIFY_LAMBDA)

                        # (1) iam:PassRole
                        # - Resource가 "*" 이면: 현재 Role을 제외한 모든 Role을 대상으로 연결
                        # - Resource가 특정 Role ARN이면: 해당 Role만 대상으로 연결
                        if service == "iam" and action == "iam:PassRole":
                            if "*" in resources:
                                for role in roles:
                                    if role == role_value:
                                        continue
                                    role_name = role["RoleName"]
                                    dst = f"{account_id}:iam_role:{role_name}"
                                    edge_id = f"edge:{name}:IAM_ROLE_CAN_PASS_ROLE:{role_name}"
                                    _add_edge(edge_id, "IAM_ROLE_CAN_PASS_ROLE", node_id, dst, "This role can pass the target IAM Role (iam:PassRole).")
                            else:
                                for res in resources:
                                    if ":role/" in res:
                                        role_name = res.split("/")[-1]
                                        dst = f"{account_id}:iam_role:{role_name}"
                                        edge_id = f"edge:{name}:IAM_ROLE_CAN_PASS_ROLE:{role_name}"
                                        _add_edge(edge_id, "IAM_ROLE_CAN_PASS_ROLE", node_id, dst, "This role can pass the target IAM Role (iam:PassRole).")

                        # (2) sts:AssumeRole
                        # - Resource가 "*" 이면: 현재 Role을 제외한 모든 Role을 대상으로 연결
                        # - Resource가 특정 Role ARN이면: 해당 Role만 대상으로 연결
                        if service == "sts" and action == "sts:AssumeRole":
                            if "*" in resources:
                                for role in roles:
                                    if role == role_value:
                                        continue
                                    role_name = role["RoleName"]
                                    dst = f"{account_id}:iam_role:{role_name}"
                                    edge_id = f"edge:{name}:IAM_ROLE_CAN_ASSUME_ROLE:{role_name}"
                                    _add_edge(edge_id, "IAM_ROLE_CAN_ASSUME_ROLE", node_id, dst, "This role can call sts:AssumeRole on the target role.")
                            else:
                                for res in resources:
                                    if ":role/" in res:
                                        role_name = res.split("/")[-1]
                                        dst = f"{account_id}:iam_role:{role_name}"
                                        edge_id = f"edge:{name}:IAM_ROLE_CAN_ASSUME_ROLE:{role_name}"
                                        _add_edge(edge_id, "IAM_ROLE_CAN_ASSUME_ROLE", node_id, dst, "This role can call sts:AssumeRole on the target role.")

                        # (3) Lambda 수정/생성/권한 부여 관련 Action
                        # - Resource가 "*" 이면: 모든 Lambda 함수 노드를 대상으로 연결
                        # - Resource가 특정 function ARN이면: 해당 함수만 대상으로 연결
                        if service == "lambda" and action in [
                            "lambda:UpdateFunctionCode",
                            "lambda:UpdateFunctionConfiguration",
                            "lambda:CreateFunction",
                            "lambda:AddPermission"
                        ]:
                            if "*" in resources:
                                for func in lambda_nodes:
                                    fname = func["FunctionName"]
                                    dst = f"{account_id}:{region}:lambda:{fname}"
                                    edge_id = f"edge:{name}:IAM_ROLE_CAN_MODIFY_LAMBDA:{fname}"
                                    _add_edge(edge_id, "IAM_ROLE_CAN_MODIFY_LAMBDA", node_id, dst, "This role can modify Lambda code/configuration.")
                            else:
                                for res in resources:
                                    if ":function/" in res:
                                        fname = res.split("/")[-1]
                                        dst = f"{account_id}:{region}:lambda:{fname}"
                                        edge_id = f"edge:{name}:IAM_ROLE_CAN_MODIFY_LAMBDA:{fname}"
                                        _add_edge(edge_id, "IAM_ROLE_CAN_MODIFY_LAMBDA", node_id, dst, "This role can modify Lambda code/configuration.")

                        # Resource 처리 로직 (기존 접근 권한 연결)
                        # - IAM_ROLE_ACCESS_* 관계는 "이 Role이 해당 서비스 리소스에 접근 가능한가"를 넓게 표현
                        # - 위의 privesc-oriented relations 와 병행하여, 분석 단계에서 더 정확한 공격 경로를 구성할 수 있음
                        if "*" in resources:  # 해당 action이 포함된 문서의 recource가 * 이라면 각 서비스의 모든 노드와 연결
                            # SQS 모든 node와 연결
                            if service == "sqs":
                                for q in sqs_nodes:
                                    qname = q["Attributes"]["QueueArn"].split(":")[-1]
                                    dst = f"{account_id}:{region}:sqs:{qname}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_SQS:{qname}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_SQS", node_id, dst, "This role gives you access to SQS.")
                            # EC2 모든 노드와 연결
                            if service == "ec2":
                                for inst in ec2_nodes:
                                    iid = inst["InstanceId"]
                                    dst = f"{account_id}:{region}:ec2:{iid}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_EC2:{iid}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_EC2", node_id, dst, "This role gives you access to EC2.")
                            # IAM 모든 노드 연결
                            if service == "iam":
                                # 모든 user와 연결
                                for user in iam_users:
                                    user_name = user["UserName"]
                                    dst = f"{account_id}:iam_user:{user_name}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_IAM:{user_name}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_IAM", node_id, dst, "This role gives you access to IAM.")
                                # 모든 role과 연결
                                for role in roles:
                                    if role == role_value:
                                        continue
                                    role_name = role["RoleName"]
                                    dst = f"{account_id}:iam_role:{role_name}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_IAM:{role_name}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_IAM", node_id, dst, "This role gives you access to IAM.")
                            # RDS 모든 노드와 연결
                            if service == "rds":
                                for inst in rds_nodes:
                                    iid = inst["DBInstanceIdentifier"]
                                    dst = f"{account_id}:{region}:rds:{iid}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_RDS:{iid}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_RDS", node_id, dst, "This role gives you access to RDS.")
                            # Lambda 모든 노드와 연결
                            if service == "lambda":
                                for func in lambda_nodes:
                                    fname = func["FunctionName"]
                                    dst = f"{account_id}:{region}:lambda:{fname}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_LAMBDA:{fname}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_LAMBDA", node_id, dst, "This role gives you access to Lambda.")
                            # Secrets Manager 모든 노드와 연결
                            if service == "secretsmanager":
                                for sec in secrets_nodes:
                                    secret_name = sec["Name"]
                                    dst = f"{account_id}:{region}:secretsmanager:{secret_name}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_SECRETSMANAGER:{secret_name}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_SECRETSMANAGER", node_id, dst, "This role gives you access to Secrets Manager.")
                        else:
                            for res in resources:
                                # 특정 user 대상인 경우 해당 user와 연결
                                if service == "iam" and ":user/" in res:
                                    user_name = res.split("/")[-1]
                                    dst = f"{account_id}:iam_user:{user_name}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_USER:{user_name}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_USER", node_id, dst, "This role gives you access to IAM User.")
                                # 특정 role 대상인 경우 해당 role과 연결
                                if service == "iam" and ":role/" in res:
                                    role_name = res.split("/")[-1]
                                    dst = f"{account_id}:iam_role:{role_name}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_ROLE:{role_name}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_ROLE", node_id, dst, "This role gives you access to IAM Role.")
                                # 특정 sqs 대상인 경우 해당 sqs와 연결
                                if service == "sqs" and ":sqs:" in res:
                                    qname = res.split(":")[-1]
                                    dst = f"{account_id}:{region}:sqs:{qname}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_SQS:{qname}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_SQS", node_id, dst, "This role gives you access to SQS Queue.")
                                # 특정 ec2 인스턴스 대상인 경우 해당 ec2 인스턴스와 연결
                                if service == "ec2" and ":ec2:" in res and ":instance/" in res:
                                    iid = res.split("/")[-1]
                                    dst = f"{account_id}:{region}:ec2:{iid}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_EC2:{iid}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_EC2", node_id, dst, "This role gives you access to EC2 Instance.")
                                # 특정 rds 인스턴스 대상인 경우 해당 rds 인스턴스와 연결
                                if service == "rds" and ":rds:" in res and ":db/" in res:
                                    db_name = res.split("/")[-1]
                                    for inst in rds_nodes:
                                        rds_name = inst["DBName"]
                                        if rds_name == db_name:
                                            rds_id = inst["DBInstanceIdentifier"]
                                            dst = f"{account_id}:{region}:rds:{rds_id}"
                                            edge_id = f"edge:{name}:IAM_ROLE_ACCESS_RDS:{rds_id}"
                                            _add_edge(edge_id, "IAM_ROLE_ACCESS_RDS", node_id, dst, "This role gives you access to RDS Instance.")
                                # 특정 Lambda 함수 대상인 경우 해당 Lambda 함수와 연결
                                if service == "lambda" and ":lambda:" in res and ":function/" in res:
                                    fname = res.split("/")[-1]
                                    dst = f"{account_id}:{region}:lambda:{fname}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_LAMBDA:{fname}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_LAMBDA", node_id, dst, "This role gives you access to Lambda Function.")
                                #특정 Secrets 대상인 경우 해당 Secrets과 연결
                                if service == "secretsmanager" and ":secretsmanager:" in res and ":secretsmanager/" in res:
                                    secret_name = res.split("/")[-1]
                                    dst = f"{account_id}:{region}:secretsmanager:{secret_name}"
                                    edge_id = f"edge:{name}:IAM_ROLE_ACCESS_SECRETSMANAGER:{secret_name}"
                                    _add_edge(edge_id, "IAM_ROLE_ACCESS_SECRETSMANAGER", node_id, dst, "This role gives you access to Secrets.")
    return edges
