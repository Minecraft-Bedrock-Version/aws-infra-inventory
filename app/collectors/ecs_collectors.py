from __future__ import annotations
from typing import Any, Dict, List

def collect_ecs(session, region: str) -> Dict[str, Any]:
    #API 호출용 객체 생성
    ecs = session.client("ecs", region_name=region)
    
    #ECS 태스크 정보가 저장될 구조 (리스트 안에 딕셔너리가 존재하며, 딕셔너리의 str 키에 어떤 형태로든 값이 들어갈 수 있음) 
    tasks: List[Dict[str, Any]] = []

    #모든 ECS 클러스터 ARN 호출
    cluster_arns = ecs.list_clusters().get("clusterArns", [])
    if cluster_arns:
    # 클러스터 상세 정보 조회
    clusters_detail = ecs.describe_clusters(clusters=cluster_arns).get("clusters", [])
    cluster_status_map = {c['clusterName']: c['status'] for c in clusters_detail}

    for cluster_arn in cluster_arns:
        cluster_name = cluster_arn.split('/')[-1] #ARN 문자열을 '/' 기준으로 잘라 마지막 요소인 이름만 추출
        print(f"[+] Processing ECS Cluster: {cluster_name}")
        
        #클러스터 내 실행 중인 태스크 ARN 목록 호출
        task_arns = ecs.list_tasks(cluster=cluster_arn).get("taskArns", [])
        
        if task_arns:
            #태스크 상세 정보 모두 조회
            tasks_detail = ecs.describe_tasks(cluster=cluster_arn, tasks=task_arns).get("tasks", [])
            
            for task in tasks_detail:
                #클러스터 이름 정보 추가
                task["ClusterName"] = cluster_name

                task_def_arn = task.get("taskDefinitionArn", "")

                if task_def_arn:
                    task_family = task_def_arn.split('/')[-1].split(':')[0]
                else:
                    task_family = "unknown"

                raw_group = task.get("group", "")
                if ":" in raw_group:
                    # 'service:privd' -> 'privd' 추출
                    task_name = raw_group.split(':')[-1]
                else:
                    # group 정보가 'service:...' 형태가 아니면 task_family 값을 사용
                    task_name = task_family

                # 최종적으로 Task 객체에 TaskName을 저장합니다.
                task["TaskName"] = task_name
                
                #태스크가 어느 EC2 위에서 돌아가는지 파악하기 위해 추가
                container_instance_arn = task.get("containerInstanceArn")
                task["HostInstanceId"] = None #매핑 실패 시, 기본값 설정
                
                if container_instance_arn:
                    #컨테이너 인스턴스 조회를 통해 실제 EC2 ID 확보
                    c_instance_detail = ecs.describe_container_instances(
                        cluster=cluster_arn, 
                        containerInstances=[container_instance_arn]
                    ).get("containerInstances", [])
                    if c_instance_detail:
                        #확보한 EC2 ID를 태스크 딕셔너리에 추가
                        task["HostInstanceId"] = c_instance_detail[0].get("ec2InstanceId")

                #태스크 정의 및 iam 권한 확인
                task_def_arn = task.get("taskDefinitionArn")
                task_def_res = ecs.describe_task_definition(taskDefinition=task_def_arn).get("taskDefinition", {})
                
                #컨테이너와 연결된 iam role의 arn 추출
                task["TaskRoleArn"] = task_def_res.get("taskRoleArn")
                
                #Docker Socket 노출 여부 확인
                task["HasDockerSocket"] = False #기본값 false, 노출 여부 발견 시 true
                container_definitions = task_def_res.get("containerDefinitions", [])
                
                for container in container_definitions:
                    mount_points = container.get("mountPoints", [])
                    for mp in mount_points:
                        if "docker.sock" in mp.get("sourceVolume", "").lower() or \
                           "docker.sock" in mp.get("containerPath", "").lower():
                            task["HasDockerSocket"] = True

                tasks.append(task)

    return {
        "region": region,
        "count": len(tasks),
        "tasks": tasks
    }
