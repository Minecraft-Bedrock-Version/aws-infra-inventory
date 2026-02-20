def extract_ecs_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        node_type = node.get("node_type")
        attrs = node.get("attributes", {})

        #ECS Cluster 노드 처리
        if node_type == "ecs_cluster":
            vector_nodes.append({
                "node_id": node.get("node_id"),
                "type": "ecs_cluster",
                "name": node.get("name"),
                "properties": {
                    "cluster_arn": attrs.get("cluster_arn"),
                    "status": attrs.get("status")
                }
            })

        #ECS Task 노드 처리
        elif node_type == "ecs_task":
            vector_nodes.append({
                "node_id": node.get("node_id"),
                "type": "ecs_task",
                "name": node.get("name"),
                "properties": {
                    "cluster_name": attrs.get("cluster_name"),
                    "host_instance_id": attrs.get("host_instance_id"),
                    "launch_type": attrs.get("launch_type"),
                    "has_docker_socket": attrs.get("has_docker_socket", False),
                    "containers": [
                        {
                            "name": c.get("name"),
                            "image": c.get("image"),
                            "cpu": c.get("cpu"),
                            "memory": c.get("memory")
                        }
                        for c in attrs.get("containers", [])
                    ]
                }
            })

    return {"nodes": vector_nodes}