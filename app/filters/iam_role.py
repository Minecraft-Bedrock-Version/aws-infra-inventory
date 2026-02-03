def extract_iam_role_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        if node.get("node_type") != "iam_role":
            continue

        attributes = node.get("attributes", {})

        # 1. Assume Role Policy 처리
        assume_role_statements = []
        assume_role_policy = attributes.get("assume_role_policy")
        if isinstance(assume_role_policy, dict):
            for stmt in assume_role_policy.get("Statement", []):
                assume_role_statements.append({
                    "Effect": stmt.get("Effect"),
                    "Action": stmt.get("Action"),
                    "Principal": stmt.get("Principal"),
                })

        # 2. Inline Policies 처리
        inline_policies_raw = attributes.get("inline_policies", [])
        inline_policies = []

        if isinstance(inline_policies_raw, list):
            for policy in inline_policies_raw:
                if not isinstance(policy, dict):
                    continue

                policy_doc = policy.get("PolicyDocument", {})
                statements = []
                for stmt in policy_doc.get("Statement", []):
                    statements.append({
                        "Action": stmt.get("Action", []),
                        "Effect": stmt.get("Effect"),
                        "Resource": stmt.get("Resource"),
                    })

                inline_policies.append({
                    "PolicyName": policy.get("PolicyName"),
                    "Statement": statements
                })

        # 3. Attached Policies 처리 (DefaultVersion만)
        attached_policies_raw = attributes.get("attached_policies", [])
        attached_policies = []

        if isinstance(attached_policies_raw, list):
            for policy in attached_policies_raw:
                if not isinstance(policy, dict):
                    continue

                for version in policy.get("Versions", []):
                    if version.get("IsDefaultVersion") is True:
                        doc = version.get("Document", {})
                        statements = []
                        for stmt in doc.get("Statement", []):
                            statements.append({
                                "Action": stmt.get("Action", []),
                                "Effect": stmt.get("Effect"),
                                "Resource": stmt.get("Resource"),
                            })

                        attached_policies.append({
                            "PolicyName": policy.get("PolicyName"),
                            "Statement": statements
                        })

        iam_role_vector_node = {
            "node_id": node.get("node_id"),
            "type": "iam_role",
            "name": node.get("name"),
            "properties": {
                "assume_role_policy": {
                    "Statement": assume_role_statements
                },
                "inline_policies": inline_policies,
                "attached_policies": attached_policies,
            }
        }

        vector_nodes.append(iam_role_vector_node)

    return {
        "nodes": vector_nodes
    }
