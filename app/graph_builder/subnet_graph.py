import json

def transform_subnet_to_graph(subnet_normalized_data):
    graph_data = {
        "schema_version": "1.0",
        "collected_at": subnet_normalized_data["collected_at"],
        "account_id": subnet_normalized_data["account_id"],
        "nodes": [],
        "edges": []
    }

    account_id = subnet_normalized_data["account_id"]

    for node in subnet_normalized_data["nodes"]:
        n_id = node["node_id"]
        res_id = node["resource_id"]
        region = n_id.split(":")[1]
        attrs = node.get("attributes", {})

        # 1. Subnet 노드 생성
        new_node = {
            "id": n_id,
            "type": "subnet",
            "name": node.get("name"),
            "arn": f"arn:aws:ec2:{region}:{account_id}:subnet/{res_id}",
            "region": region,
            "properties": {
                "vpc_id": attrs.get("vpc_id"),
                "cidr_block": attrs.get("cidr"),
                "availability_zone": attrs.get("az"),
                "visibility": attrs.get("visibility"),
                "route_table_id": attrs.get("route_table_id"),
                "assign_ipv6_on_creation": False
            }
        }
        graph_data["nodes"].append(new_node)

        # 2. MEMBER_OF 엣지 생성 (Subnet -> VPC)
        vpc_id = attrs.get("vpc_id")
        if vpc_id:
            graph_data["edges"].append({
                "id": f"edge:{res_id}:MEMBER_OF:{vpc_id}",
                "relation": "MEMBER_OF",
                "src": n_id,
                "src_label": f"subnet:{node.get('name')}",
                "dst": f"{account_id}:{region}:vpc:{vpc_id}",
                "dst_label": "vpc:parent", # 대상 VPC 이름은 VPC 변환기에서 처리되므로 레이블만 지정
                "directed": True,
                "conditions": []
            })

        # 3. ASSOCIATED_WITH 엣지 생성 (Subnet -> Route Table)
        rt_id = attrs.get("route_table_id")
        if rt_id:
            graph_data["edges"].append({
                "id": f"edge:{res_id}:ASSOCIATED_WITH:{rt_id}",
                "relation": "ASSOCIATED_WITH",
                "src": n_id,
                "src_label": f"subnet:{node.get('name')}",
                "dst": f"{account_id}:{region}:route_table:{rt_id}",
                "dst_label": f"route_table:{rt_id}",
                "directed": True,
                "conditions": []
            })

    return graph_data