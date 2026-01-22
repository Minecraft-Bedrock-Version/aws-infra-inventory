def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False


def extract_ec2_for_vector(normalized_data: dict) -> dict:

    vector_nodes = []

    for node in normalized_data.get("nodes", []):
        if node.get("node_type") != "ec2":
            continue

        attributes = node.get("attributes", {})

        ec2_vector_node = {
            "node_type": "ec2",
            "node_id": node.get("node_id"),
            "attributes": {
                "public": to_bool(attributes.get("public")),
                "sqs_info": {
                    "detected": to_bool(
                        attributes.get("sqs_info", {}).get("detected")
                    )
                },
                "rds_info": {
                    "detected": to_bool(
                        attributes.get("rds_info", {}).get("detected")
                    )
                }
            }
        }

        vector_nodes.append(ec2_vector_node)

    return {
        "nodes": vector_nodes
    }
