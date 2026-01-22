def extract_route_table_for_vector(normalized_data: dict) -> dict:
    vector_nodes = []

    for node in normalized_data.get("nodes", []):
        if node.get("node_type") != "route_table":
            continue

        attributes = node.get("attributes", {})

        route_table_vector_node = {
            "node_type": "route_table",
            "node_id": node.get("node_id"),
            "attributes": {
                "type": attributes.get("type")
            }
        }

        vector_nodes.append(route_table_vector_node)

    return {
        "nodes": vector_nodes
    }
