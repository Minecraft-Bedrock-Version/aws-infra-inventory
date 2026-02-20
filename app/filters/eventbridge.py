def extract_eventbridge_for_vector(graph_data: dict) -> dict:

    vector_nodes = []
    for node in graph_data.get("nodes", []):

        if node.get("node_type") != "eventbridge":
            continue
        attr = node.get("attributes")
        targets = attr.get("targets")
        target_arns = [t.get("target_arn") for t in targets]
        eventbridge_vector_node = {
            "node_id": node.get("node_id"),
            "type": "eventbridge",
            "name": node.get("name"),
            "attributes":{
                "state": attr.get("state"),
                "target_arn": target_arns
            }
        }

        vector_nodes.append(eventbridge_vector_node)

    return {
        "nodes": vector_nodes
    }