def extract_lambda_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        node_type = node.get("node_type")
        event = node.get("event_source_mapping",{})
        
        if node_type == "lambda":
            vector_nodes.append({
                "node_id": node.get("node_id"),
                "type": "lambda",
                "name": node.get("name"),
                "properties": {
                    "event_source_arn": event.get("event_source_arn")
                }
            })

    return {"nodes": vector_nodes}