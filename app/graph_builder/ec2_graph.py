from __future__ import annotations
from typing import Any, Dict
import re

#UserData 내부에서 SQS 와 RDS 주소를 찾기 위한 정규표현식
SQS_PATTERN = r"(https://sqs\.[a-z0-9-]+\.amazonaws\.com/[^\s'\"]+)"
RDS_PATTERN = r"[^\s'\"/]+\.([a-z0-9-]+)\.rds\.amazonaws\.com"


def graph_ec2(raw_payload: Dict[str, Any], account_id: str, region: str, node=None) -> Dict[str, Any]:
    
    instances = raw_payload.get("ec2", {}).get("instances", [])
    edges = []
    seen_edges = set() #edge 중복 생성을 막기위한 set

    ecs_data = raw_payload.get("ecs", {})
    all_tasks = ecs_data.get("tasks", []) 
    task_defs = ecs_data.get("task_definitions", [])
    clusters = ecs_data.get("clusters", [])

    #ContainerInstanceArn을 키로, EC2 InstanceId를 값으로 갖는 매핑 테이블 
    ci_to_ec2_map = {
        ci.get("containerInstanceArn"): ci.get("ec2InstanceId")
        for cluster in clusters 
        for ci in cluster.get("containerInstances", [])
        if ci.get("containerInstanceArn") and ci.get("ec2InstanceId")
    }
    
    for instance_value in instances: #raw data에서 인스턴스를 하나씩 조회
        instance_id = instance_value.get("InstanceId")
        node_id = f"{account_id}:{region}:ec2:{instance_id}"

        # (1) EC2의 퍼블릭 인터넷 접근성 (EC2_PUBLIC)              
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

        # (2) UserData 분석을 통한 리소스 접근
        user_data = instance_value.get("UserData") or "" #user data 읽어옴
        
        #SQS
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

        #RDS         
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
                        

        # (3) IAM 역할 연결 (HAS_IAM_ROLE)
        iam_profile = instance_value.get("IamInstanceProfile", {})
        profile_arn = iam_profile.get("Arn")

        if profile_arn:
            role_name = profile_arn.split('/')[-1] #arn에서 role의 이름 추출
            role_node_id = f"{account_id}:iam_role:{role_name}"

            edge_id = f"edge:{instance_id}:HAS_IAM_ROLE:{role_name}"
            if edge_id not in seen_edges:
                seen_edges.add(edge_id)
                edges.append({
                    "id": edge_id,
                    "relation": "HAS_IAM_ROLE",
                    "src": node_id,
                    "dst": role_node_id,
                    "directed": True,
                    "conditions": "EC2 instance is associated with an IAM Instance Profile."
                })

        # (4) ECS 클러스터 구성원 확인 (MEMBER_OF_ECS_CLUSTER)
        ecs_clusters = raw_payload.get("ecs", {}).get("clusters", [])
        for cluster in ecs_clusters:
            cluster_name = cluster.get("clusterName")
            container_instances = cluster.get("containerInstances", []) #클러스터 내부에 등록된 인스턴스 목록을 가져옴
            for ci in container_instances:
                if ci.get("ec2InstanceId") == instance_id: #ECS가 가져온 인스턴스 ID가 현재 루프의 인스턴스 ID와 일치한다면
                    edge_id = f"edge:{instance_id}:MEMBER_OF_ECS:{cluster_name}" #관계 생성
                    if edge_id not in seen_edges:
                        seen_edges.add(edge_id)
                        cluster_node_id = f"{account_id}:{region}:ecs_cluster:{cluster_name}"
                        edges.append({
                            "id": edge_id,
                            "relation": "MEMBER_OF_ECS_CLUSTER",
                            "src": node_id,
                            "dst": cluster_node_id,
                            "directed": True,
                            "conditions": "EC2 is registered as a Container Instance in this ECS cluster."
                        })
    
        # (4) ECS 관련 호스팅 및 보안 분석
        for task in all_tasks:
            target_ci_arn = task.get("containerInstanceArn") #Task가 실행 중인 ec2 인스턴스 arn 가져옴
            
            if ci_to_ec2_map.get(target_ci_arn) == instance_id: #매핑 테이블에서 arn이 현재 순회 중인 ec2 id와 일치하는지 확인
                task_def_arn = task.get("taskDefinitionArn", "") #task definition arn에서 이름 추출
                task_name = task_def_arn.split('/')[-1].split(':')[0]
                task_id = task.get("taskArn", "").split('/')[-1] #task arn에서 고유 id 추출

                # (4-1) EC2가 태스크를 실행 중 (HOSTS_ECS_TASK)
                edge_id = f"edge:{instance_id}:HOSTS_TASK:{task_id}"
                if edge_id not in seen_edges:
                    seen_edges.add(edge_id)
                    task_node_id = f"{account_id}:{region}:ecs_task/{task_id}"
                    edges.append({
                        "id": edge_id,
                        "relation": "HOSTS_ECS_TASK",
                        "src": node_id,
                        "dst": task_node_id,
                        "directed": True,
                        "conditions": f"The EC2 instance is hosting the ECS Task: {task_name}."
                    })

                # (4-2) 도커 소켓 노출 위험 (DOCKER_SOCKET_EXPOSED)
                current_def = next((td for td in task_defs if td.get("taskDefinitionArn") == task_def_arn), {}) #task definition 조회
                volumes = current_def.get("volumes", []) #voluemes 목록에서
                if any(v.get("host", {}).get("sourcePath") == "/var/run/docker.sock" for v in volumes): #docker.sock 이 포함되어 있다면
                    vuln_edge_id = f"edge:{task_id}:DOCKER_SOCKET_EXPOSED:{instance_id}" #엣지 생성
                    if vuln_edge_id not in seen_edges:
                        seen_edges.add(vuln_edge_id)
                        task_node_id = f"{account_id}:{region}:ecs_task/{task_id}"
                        edges.append({
                            "id": vuln_edge_id,
                            "relation": "DOCKER_SOCKET_EXPOSED",
                            "src": task_node_id, # 출발이 Task (컨테이너에서 호스트로 탈옥하므로)
                            "dst": node_id,
                            "directed": True,
                            "conditions": "Docker socket is mounted from the host. The container can control the host EC2 via Docker API."
                        })

                # (4-3) 네트워크 스택 공유 및 IMDS 보안 분석 (SHARED_NETWORK_STACK)
                if current_def.get("networkMode") == "host":
                    metadata_options = instance_value.get("MetadataOptions", {})
                    http_endpoint = metadata_options.get("HttpEndpoint") # 메타데이터 서비스 활성화 여부
                    http_tokens = metadata_options.get("HttpTokens")     # 'required'이면 v2, 'optional'이면 v1
                    net_edge_id = f"edge:{task_id}:SHARED_NETWORK_STACK:{instance_id}"
                    if net_edge_id not in seen_edges:
                        seen_edges.add(net_edge_id)
                        # IMDSv1이 허용되어 있는 경우
                        if http_endpoint == "enabled" and http_tokens == "optional":
                            status = "IMDSv1 enabled. Potential for IAM credential exfiltration."
                        # IMDSv2가 강제되어 있는 경우
                        elif http_endpoint == "enabled" and http_tokens == "required":
                            status = "IMDSv2 enforced. Metadata access is restricted by session tokens."
                        # 메타데이터 서비스 자체가 꺼져 있는 경우 엣지 생성 안함
                        if status != "Unknown":
                            edges.append({
                                "id": net_edge_id,
                                "relation": "SHARED_NETWORK_STACK",
                                "src": task_node_id,
                                "dst": node_id,
                                "directed": True,
                                "conditions": status
                            })

    return edges
