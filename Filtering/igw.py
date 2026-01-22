def extract_igw_for_vector(normalized_data: dict) -> dict:
    vector_nodes = []

    for node in normalized_data.get("nodes", []):
        if node.get("node_type") != "internet_gateway":
            continue

        attributes = node.get("attributes", {})

        igw_vector_node = {
            "node_type": "internet_gateway",
            "node_id": node.get("node_id"),
            "attributes": {
                "state": attributes.get("state")
            }
        }

        vector_nodes.append(igw_vector_node)

    return {
        "nodes": vector_nodes
    }
