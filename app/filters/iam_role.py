def extract_iam_role_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        if node.get("type") != "iam_role":
            continue

        properties = node.get("properties", {})

        # 1. Assume Role Policy 처리 (데이터가 dict인지 확인)
        assume_role_statements = []
        assume_role_policy = properties.get("assume_role_policy")
        if isinstance(assume_role_policy, dict):
            for stmt in assume_role_policy.get("Statement", []):
                assume_role_statements.append({
                    "Effect": stmt.get("Effect"),
                    "Action": stmt.get("Action")
                })

        # 2. Inline Policies 처리 (핵심 에러 지점 해결)
        inline_policies_raw = properties.get("inline_policies", [])
        inline_policies = []
        
        # 리스트인 경우에만 루프 실행
        if isinstance(inline_policies_raw, list):
            for policy in inline_policies_raw:
                if not isinstance(policy, dict):
                    continue
                
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
            "node_id": node.get("node_id") or node.get("id"), # ID 키 호환성 보장
            "type": "iam_role",
            "name": node.get("name"),
            "properties": {
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