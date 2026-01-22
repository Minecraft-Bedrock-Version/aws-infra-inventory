def extract_sqs_for_vector(normalized_data: dict) -> dict:
    vector_nodes = []

    for node in normalized_data.get("nodes", []):
        if node.get("node_type") != "sqs":
            continue

        sqs_vector_node = {
            "node_type": "sqs",
            "node_id": node.get("node_id")
        }

        vector_nodes.append(sqs_vector_node)

    return {
        "nodes": vector_nodes
    }
