def extract_vpc_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        if node.get("node_type") != "vpc":
            continue

        vpc_vector_node = {
            "node_id": node.get("node_id"),
            "type": "vpc",
            "name": node.get("name")
        }
        vector_nodes.append(vpc_vector_node)

    return {"nodes": vector_nodes}