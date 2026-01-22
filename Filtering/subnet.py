def extract_subnet_for_vector(normalized_data: dict) -> dict:
    vector_nodes = []

    for node in normalized_data.get("nodes", []):
        if node.get("node_type") != "subnet":
            continue

        attributes = node.get("attributes", {})

        subnet_vector_node = {
            "node_type": "subnet",
            "node_id": node.get("node_id"),
            "attributes": {
                "visibility": attributes.get("visibility")
            }
        }

        vector_nodes.append(subnet_vector_node)

    return {
        "nodes": vector_nodes
    }
