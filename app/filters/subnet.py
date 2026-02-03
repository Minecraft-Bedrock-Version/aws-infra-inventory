def extract_subnet_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        if node.get("node_type") != "subnet":
            continue

        props = node.get("attributes", {})

        subnet_vector_node = {
            "node_id": node.get("node_id"),
            "type": "subnet",
            "name": node.get("name"),
            "properties": {
                "vpc_id": props.get("vpc_id")
            }
        }
        vector_nodes.append(subnet_vector_node)

    return {"nodes": vector_nodes}