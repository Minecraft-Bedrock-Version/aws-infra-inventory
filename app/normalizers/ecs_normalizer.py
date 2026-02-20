from __future__ import annotations
from typing import Any, Dict, List
from datetime import timezone

def normalize_ecs(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:

    ecs_data = raw_payload.get("ecs", {})
    tasks = ecs_data.get("tasks", [])
    nodes = []
    seen_clusters = set() #클러스터 노드 중복 생성 방지용

    for task_value in tasks:

        #각 필드를 채우기 위한 값
        node_type = "ecs_task"
        task_arn = task_value.get("taskArn", "")
        task_id = task_arn.split('/')[-1] if task_arn else "unknown"
        node_id = f"{account_id}:{region}:ecs_task:{task_id}"
        name = task_value.get("TaskName", "unknown")
        cluster_name = task_value.get("ClusterName") or task_value.get("clusterArn", "").split('/')[-1]
        task_definition = task_value.get("taskDefinitionArn")
        host_instance_id = task_value.get("HostInstanceId")
        launch_type = task_value.get("launchType")
        last_status = task_value.get("lastStatus")
        has_docker_socket = task_value.get("HasDockerSocket", False)
        # 컨테이너 정보 정리
        containers = [
            {k: c.get(k) for k in ["name", "image", "cpu", "memory"]}
            for c in task_value.get("containers", [])
        ]

        cluster_node_id = f"{account_id}:{region}:ecs_cluster:{cluster_name}"

        #ECS Cluster Node
        if cluster_node_id not in seen_clusters:
            current_status = task_value.get("ClusterStatus", "UNKNOWN")

            cluster_node = {
                "node_type": "ecs_cluster",
                "node_id": cluster_node_id,
                "resource_id": cluster_name,
                "name": cluster_name,
                "account_id": account_id,
                "region": region,
                "attributes": {
                    "cluster_arn": task_value.get("clusterArn"),
                    "status": current_status
                }
            }
            nodes.append(cluster_node)
            seen_clusters.add(cluster_node_id)

        #ECS task Node
        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": task_id,
            "name": name,
            "account_id": account_id,
            "region": region,
            "attributes": {
                "task_arn": task_arn,
                "cluster_name": cluster_name,
                "task_definition": task_definition,
                "host_instance_id": host_instance_id,
                "launch_type": launch_type,
                "last_status": last_status,
                "has_docker_socket": has_docker_socket,
                "containers": containers
            }
        }
        nodes.append(node)

    return nodes
