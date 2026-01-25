def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False

def extract_ec2_for_vector(graph_data: dict) -> dict:

    vector_nodes = []

    for node in graph_data.get("nodes", []):
        
        print("ec2")
        print("ec2")
        print("ec2")
        print("ec2")
        print("ec2")
        print("ec2")
        print(node)

        if node.get("type") != "ec2_instance":
            continue

        properties = node.get("properties", {})

        ec2_vector_node = {
            "node_id": node.get("node_id") or node.get("id"),
            "type": "ec2",
            "name": node.get("name"), 
            "properties": {
                "public": to_bool(properties.get("public")),
                "sqs_info": {
                    "detected": to_bool(
                        properties.get("sqs_info", {}).get("detected")
                    )
                },
                "rds_info": {
                    "detected": to_bool(
                        properties.get("rds_info", {}).get("detected")
                    )
                }
            }
        }

        vector_nodes.append(ec2_vector_node)

    return {
        "nodes": vector_nodes
    }