def extract_iam_role_for_vector(normalized_data: dict) -> dict:
    vector_nodes = []

    for node in normalized_data.get("nodes", []):
        if node.get("node_type") != "iam_role":
            continue

        attributes = node.get("attributes", {})

        assume_role_statements = []
        for stmt in attributes.get("assume_role_policy", {}).get("Statement", []):
            assume_role_statements.append({
                "Effect": stmt.get("Effect"),
                "Action": stmt.get("Action")
            })

        inline_policies = []
        for policy in attributes.get("inline_policies", []):
            statements = []
            for stmt in policy.get("Statement", []):
                statements.append({
                    "Action": stmt.get("Action", []),
                    "Effect": stmt.get("Effect")
                })
            inline_policies.append({
                "Statement": statements
            })

        iam_role_vector_node = {
            "node_type": "iam_role",
            "node_id": node.get("node_id"),
            "attributes": {
                "assume_role_policy": {
                    "Statement": assume_role_statements
                },
                "inline_policies": inline_policies
            }
        }

        vector_nodes.append(iam_role_vector_node)

    return {
        "nodes": vector_nodes
    }
