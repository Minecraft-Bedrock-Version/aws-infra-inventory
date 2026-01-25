def extract_lambda_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        node_type = node.get("type")
        
        if node_type == "lambda_function":
            vector_nodes.append({
                "node_id": node.get("node_id") or node.get("id"),
                "type": "lambda_function",
                "name": node.get("name"),
                "properties": {}
            })

        elif node_type == "lambda_event_source_mapping":
            props = node.get("properties", {})
            vector_nodes.append({
                "node_id": node.get("node_id") or node.get("id"),
                "type": "lambda_event_source_mapping",
                "name": node.get("name"),
                "properties": {
                    "state": props.get("state"),
                    "source": props.get("source") # relationships 정보를 properties로 통합
                }
            })

    return {"nodes": vector_nodes}