def extract_iam_user_for_vector(normalized_data: dict) -> dict:
    vector_nodes = []

    for node in normalized_data.get("nodes", []):
        if node.get("node_type") != "iam_user":
            continue

        attributes = node.get("attributes", {})

        inline_policies = []
        for policy in attributes.get("inline_policies", []):
            statements = []

            for stmt in policy.get("Statement", []):
                statements.append({
                    "Effect": stmt.get("Effect"),
                    "Action": stmt.get("Action")
                })

            if statements:
                inline_policies.append({
                    "Statement": statements
                })

        iam_user_vector_node = {
            "node_type": "iam_user",
            "node_id": node.get("node_id"),
            "attributes": {
                "inline_policies": inline_policies
            }
        }

        vector_nodes.append(iam_user_vector_node)

    return {
        "nodes": vector_nodes
    }
