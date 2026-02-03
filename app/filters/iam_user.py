def extract_iam_user_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    user_nodes = graph_data.get("iam_user", {}).get("nodes", []) or graph_data.get("nodes", [])

    for node in user_nodes:
        if node.get("node_type") != "iam_user":
            continue

        attributes = node.get("attributes", {})

        inline_policies = []
        attached_policies = []
        group_policies = []

        # -------- Inline Policies --------
        for policy in attributes.get("inline_policies", []):
            if not isinstance(policy, dict):
                continue

            policy_doc = policy.get("PolicyDocument", {})
            for stmt in policy_doc.get("Statement", []):
                inline_policies.append({
                    "Effect": stmt.get("Effect"),
                    "Action": stmt.get("Action"),
                    "Resource": stmt.get("Resource"),
                })

        # -------- Attached Policies --------
        for policy in attributes.get("attached_policies", []):
            if not isinstance(policy, dict):
                continue

            for version in policy.get("Versions", []):
                if version.get("IsDefaultVersion") is True:
                    for stmt in version.get("Document", {}).get("Statement", []):
                        attached_policies.append({
                            "Effect": stmt.get("Effect"),
                            "Action": stmt.get("Action"),
                            "Resource": stmt.get("Resource"),
                        })

        # -------- Group Policies --------
        for group_policy_list in attributes.get("group_policies", []):
            if not isinstance(group_policy_list, list):
                continue

            for policy in group_policy_list:
                if not isinstance(policy, dict):
                    continue

                policy_doc = policy.get("PolicyDocument", {})
                for stmt in policy_doc.get("Statement", []):
                    group_policies.append({
                        "Effect": stmt.get("Effect"),
                        "Action": stmt.get("Action"),
                        "Resource": stmt.get("Resource"),
                    })

        iam_user_vector_node = {
            "node_id": node.get("node_id"),
            "type": "iam_user",
            "name": node.get("name"),
            "properties": {
                "inline_policies": inline_policies,
                "attached_policies": attached_policies,
                "group_policies": group_policies
            }
        }

        vector_nodes.append(iam_user_vector_node)

    return {"nodes": vector_nodes}
