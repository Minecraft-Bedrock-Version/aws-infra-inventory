def extract_iam_user_for_vector(graph_data: dict) -> dict:
    vector_nodes = []

    for node in graph_data.get("nodes", []):
        if node.get("type") != "iam_user":
            continue

        props = node.get("properties", {})
        
        # [수정] inline_policies를 가져온 후 리스트인지 확인
        inline_policies_raw = props.get("inline_policies", [])
        inline_policies = []

        if isinstance(inline_policies_raw, list):
            for policy in inline_policies_raw:
                # 개별 정책이 dict 형태인지 한 번 더 확인
                if not isinstance(policy, dict):
                    continue
                    
                statements = []
                # Statement가 리스트인지 확인하며 루프
                raw_statements = policy.get("Statement", [])
                if isinstance(raw_statements, list):
                    for stmt in raw_statements:
                        statements.append({
                            "Effect": stmt.get("Effect"),
                            "Action": stmt.get("Action")
                        })

                if statements:
                    inline_policies.append({"Statement": statements})

        iam_user_vector_node = {
            # GraphAssembler 포맷에 따라 id 또는 node_id 선택
            "node_id": node.get("node_id") or node.get("id"),
            "type": "iam_user",
            "name": node.get("name"),
            "properties": {
                "inline_policies": inline_policies
            }
        }
        vector_nodes.append(iam_user_vector_node)

    return {"nodes": vector_nodes}