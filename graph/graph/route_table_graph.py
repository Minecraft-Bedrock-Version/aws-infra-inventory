import json

def transform_route_table_to_graph(rt_normalized_data):

    graph_data = {
        "schema_version": "1.0",
        "collected_at": rt_normalized_data["collected_at"],
        "account_id": rt_normalized_data["account_id"],
        "nodes": [],
        "edges": []
    }

    account_id = rt_normalized_data["account_id"]

    for node in rt_normalized_data["nodes"]:
        res_id = node["resource_id"]
        # ID 포맷 정규화 
        region = node["node_id"].split(":")[1]
        target_node_id = f"{account_id}:{region}:route_table:{res_id}"
        attrs = node.get("attributes", {})
        rels = node.get("relationships", {})

        # Route Table 노드 생성
        new_node = {
            "id": target_node_id,
            "type": "route_table",
            "name": node.get("name"),
            "arn": f"arn:aws:ec2:{region}:{account_id}:route-table/{res_id}",
            "region": region,
            "properties": {
                "vpc_id": attrs.get("vpc_id"),
                "main": attrs.get("main", False),
                "visibility": attrs.get("type"), # 정규화 데이터의 type을 visibility로 매핑
                "associated_subnets": rels.get("associated_subnets", []),
                "routes": [ 
                    { "destination": "10.10.0.0/16", "target": "local", "state": "active" }
                ]
            }
        }
        # public 타입일 경우 IGW 라우팅 정보 예시 추가 (요청 포맷 반영)
        if attrs.get("type") == "public":
            new_node["properties"]["routes"].append(
                { "destination": "0.0.0.0/0", "target": "igw-unknown", "state": "active" }
            )
            
        graph_data["nodes"].append(new_node)

        # 2. MEMBER_OF 엣지 생성 (RT -> VPC)
        vpc_id = attrs.get("vpc_id")
        if vpc_id:
            graph_data["edges"].append({
                "id": f"edge:{res_id}:MEMBER_OF:{vpc_id}",
                "relation": "MEMBER_OF",
                "src": target_node_id,
                "src_label": f"route_table:{node.get('name')}",
                "dst": f"{account_id}:{region}:vpc:{vpc_id}",
                "dst_label": "vpc:parent",
                "directed": True,
                "conditions": []
            })

        # 3. ASSOCIATED_WITH 엣지 생성 (Subnet -> RT)
        for subnet_id in rels.get("associated_subnets", []):
            graph_data["edges"].append({
                "id": f"edge:{subnet_id}:ASSOCIATED_WITH:{res_id}",
                "relation": "ASSOCIATED_WITH",
                "src": f"{account_id}:{region}:subnet:{subnet_id}",
                "src_label": f"subnet:{subnet_id}", # 실제 Subnet 이름은 Subnet 파일에서 처리
                "dst": target_node_id,
                "dst_label": f"route_table:{node.get('name')}",
                "directed": True,
                "conditions": []
            })

    return graph_data
