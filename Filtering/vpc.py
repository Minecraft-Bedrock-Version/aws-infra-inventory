def extract_vpc_for_vector(normalized_data: dict) -> dict:
    vector_nodes = []

    for node in normalized_data.get("nodes", []):
        if node.get("node_type") != "vpc":
            continue

        vpc_vector_node = {
            "node_type": "vpc",
            "node_id": node.get("node_id")
        }

        vector_nodes.append(vpc_vector_node)

    return {
        "nodes": vector_nodes
    }
