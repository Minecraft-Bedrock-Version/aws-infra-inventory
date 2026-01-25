def extract_rds_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        if node.get("type") != "rds_instance":
            continue

        vector_nodes.append({
            "node_id": node.get("node_id") or node.get("id"),
            "type": "rds_instance",
            "name": node.get("name"),
            "properties": {}
        })

    return {"nodes": vector_nodes}