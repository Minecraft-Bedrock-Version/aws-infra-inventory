def extract_route_table_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        if node.get("type") != "route_table":
            continue

        props = node.get("properties", {})

        route_table_vector_node = {
            "node_id": node.get("node_id") or node.get("id"),
            "type": "route_table",
            "name": node.get("name"),
            "properties": {
                "type": props.get("type")
            }
        }
        vector_nodes.append(route_table_vector_node)

    return {"nodes": vector_nodes}