from __future__ import annotations
from typing import Any, Dict
import re

def graph_ecs(raw_payload: Dict[str, Any], account_id: str, region: str) -> List[Dict[str, Any]]:

    # 서비스 node들 모두 미리 불러와두기
    ecs_data = raw_payload.get("ecs", {})
    all_tasks = ecs_data.get("tasks", []) 
    
    edges = []
    seen_edges = set() #엣지 중복 생성 방지

    for task in all_tasks: #태스크 목록 순회하면서
        task_arn = task.get("taskArn", "") #task arn에서 id 추출
        task_id = task_arn.split('/')[-1] if task_arn else "unknown" #태스크 ID 추출
        task_node_id = f"{account_id}:{region}:ecs_task:{task_id}"# 태스크 노드 ID 정의
        
        # (1) 태스크가 ECS 클러스터에 속함 (MEMBER_OF)
        cluster_name = task.get("ClusterName") #태스크를 실행한 클러스터 명칭 추출
        if cluster_name:
            cluster_node_id = f"{account_id}:{region}:ecs_cluster:{cluster_name}"
            edge_id = f"edge:{task_id}:MEMBER_OF:{cluster_name}"
            if edge_id not in seen_edges:
                seen_edges.add(edge_id)
                edges.append({
                    "id": edge_id,
                    "relation": "MEMBER_OF",
                    "src": task_node_id,
                    "dst": cluster_node_id,
                    "directed": True,
                    "conditions": "This Task belongs to the Cluster."
                })

        # (2) 태스크가 IAM 역할을 사용함 (HAS_IAM_ROLE)
        task_role_arn = task.get("TaskRoleArn")
        if task_role_arn:
            role_name = task_role_arn.split('/')[-1]
            role_node_id = f"{account_id}:iam_role:{role_name}"
            
            edge_id = f"edge:{task_id}:HAS_TASK_ROLE:{role_name}"
            if edge_id not in seen_edges:
                seen_edges.add(edge_id)
                edges.append({
                    "id": edge_id,
                    "relation": "HAS_IAM_ROLE",
                    "src": task_node_id,
                    "dst": role_node_id,
                    "directed": True,
                    "conditions": "This ECS task assumes an IAM role for AWS service access."
                })

        # (3) 태스크와 호스트 EC2 간의 물리적 배치 및 보안 관계
        host_instance_id = task.get("HostInstanceId")#태스크가 구동 중인 EC2 인스턴스 ID 추출
        if host_instance_id:
            ec2_node_id = f"{account_id}:{region}:ec2:{host_instance_id}"
            
            # (3-1) EC2가 태스크를 호스팅함 (HOSTS)
            host_edge_id = f"edge:{host_instance_id}:HOSTS:{task_id}"
            if host_edge_id not in seen_edges:
                seen_edges.add(host_edge_id)
                edges.append({
                    "id": host_edge_id,
                    "relation": "HOSTS",
                    "src": ec2_node_id,
                    "dst": task_node_id,
                    "directed": True,
                    "conditions": f"This EC2 instance hosts this Task."
                })

            # (3-2) Docker Socket 노출 위험 (DOCKER_SOCKET_EXPOSED)
            if task.get("HasDockerSocket") is True:
                ds_edge_id = f"edge:{task_id}:DOCKER_SOCKET:{host_instance_id}"
                if ds_edge_id not in seen_edges:
                    seen_edges.add(ds_edge_id)
                    edges.append({
                        "id": ds_edge_id,
                        "relation": "DOCKER_SOCKET_EXPOSED",
                        "src": task_node_id,
                        "dst": ec2_node_id,
                        "directed": True,
                        "conditions": "WARNING: Docker socket is exposed to this Task."
                    })
            
            # (3-3) 네트워크 스택 공유 (SHARED_NETWORK_STACK)
            # - 컨테이너가 호스트의 네트워크 망을 그대로 사용하는 경우를 정의합니다.
            if task.get("NetworkMode") == "host":
                net_edge_id = f"edge:{task_id}:SHARED_NETWORK:{host_instance_id}"
                if net_edge_id not in seen_edges:
                    seen_edges.add(net_edge_id)
                    edges.append({
                        "id": net_edge_id,
                        "relation": "SHARED_NETWORK_STACK",
                        "src": task_node_id, 
                        "dst": ec2_node_id, 
                        "directed": True,
                        "conditions": "This Task shares the host EC2 network stack."
                    })

    return edges
