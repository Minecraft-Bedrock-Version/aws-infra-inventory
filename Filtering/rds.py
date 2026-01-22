def extract_rds_for_vector(normalized_data: dict) -> dict:
    vector_nodes = []

    for node in normalized_data.get("nodes", []):
        if node.get("node_type") != "rds_instance":
            continue

        rds_vector_node = {
            "node_type": "rds_instance",
            "node_id": node.get("node_id")
        }

        vector_nodes.append(rds_vector_node)

    return {
        "nodes": vector_nodes
    }
