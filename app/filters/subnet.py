def extract_subnet_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        if node.get("type") != "subnet":
            continue

        props = node.get("properties", {})

        subnet_vector_node = {
            "node_id": node.get("node_id") or node.get("id"),
            "type": "subnet",
            "name": node.get("name"),
            "properties": {
                "visibility": props.get("visibility")
            }
        }
        vector_nodes.append(subnet_vector_node)

    return {"nodes": vector_nodes}