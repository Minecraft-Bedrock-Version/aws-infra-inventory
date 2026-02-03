def extract_igw_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        if node.get("node_type") != "igw":
            continue

        props = node.get("attributes", {})

        igw_vector_node = {
            "node_id": node.get("node_id"),
            "type": "igw",
            "name": node.get("name"),
            "properties": {
                "attached_vpc_id": props.get("attached_vpc_id"),
                "state": props.get("state")
            }
        }
        vector_nodes.append(igw_vector_node)

    return {"nodes": vector_nodes}