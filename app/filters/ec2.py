def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False

def extract_ec2_for_vector(graph_data: dict) -> dict:

    vector_nodes = []

    for node in graph_data.get("nodes", []):

        if node.get("node_type") != "ec2_instance":
            continue

        ec2_vector_node = {
            "node_id": node.get("node_id"),
            "type": "ec2",
            "name": node.get("name")
        }

        vector_nodes.append(ec2_vector_node)

    return {
        "nodes": vector_nodes
    }