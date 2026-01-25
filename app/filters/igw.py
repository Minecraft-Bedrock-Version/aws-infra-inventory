def extract_igw_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        if node.get("type") != "internet_gateway":
            continue

        props = node.get("properties", {})

        igw_vector_node = {
            "node_id": node.get("node_id") or node.get("id"),
            "type": "internet_gateway",
            "name": node.get("name"),
            "properties": {
                "state": props.get("state")
            }
        }
        vector_nodes.append(igw_vector_node)

    return {"nodes": vector_nodes}