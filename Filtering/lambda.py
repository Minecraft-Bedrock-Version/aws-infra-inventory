def extract_lambda_for_vector(normalized_data: dict) -> dict:
    vector_nodes = []

    for node in normalized_data.get("nodes", []):

        if node.get("node_type") == "lambda_function":
            lambda_node = {
                "node_type": "lambda_function",
                "node_id": node.get("node_id")
            }
            vector_nodes.append(lambda_node)

        elif node.get("node_type") == "lambda_event_source_mapping":
            attributes = node.get("attributes", {})
            relationships = node.get("relationships", {})

            event_mapping_node = {
                "node_type": "lambda_event_source_mapping",
                "node_id": node.get("node_id"),
                "attributes": {
                    "state": attributes.get("state")
                },
                "relationships": {
                    "source": relationships.get("source")
                }
            }

            vector_nodes.append(event_mapping_node)

    return {
        "nodes": vector_nodes
    }
