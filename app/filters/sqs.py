def extract_sqs_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        if node.get("node_type") != "sqs":
            continue

        sqs_vector_node = {
            "node_id": node.get("node_id"),
            "type": "sqs",
            "name": node.get("name")
        }
        vector_nodes.append(sqs_vector_node)

    return {"nodes": vector_nodes}