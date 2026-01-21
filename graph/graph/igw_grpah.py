import json

def transform_igw_to_graph(igw_normalized_data):
    graph_data = {
        "schema_version": "1.0",
        "collected_at": igw_normalized_data["collected_at"],
        "account_id": igw_normalized_data["account_id"],
        "nodes": [],
        "edges": []
    }

    account_id = igw_normalized_data["account_id"]

    for node in igw_normalized_data["nodes"]:
        res_id = node["resource_id"]
        region = node["node_id"].split(":")[1]
        target_node_id = f"{account_id}:{region}:internet_gateway:{res_id}"
        attrs = node.get("attributes", {})

        # 1. IGW 노드 생성
        new_node = {
            "id": target_node_id,
            "type": "internet_gateway",
            "name": node.get("name"),
            "arn": f"arn:aws:ec2:{region}:{account_id}:internet-gateway/{res_id}",
            "region": region,
            "properties": {
                "attached_vpc_id": attrs.get("attached_vpc_id"),
                "state": attrs.get("state")
            }
        }
        graph_data["nodes"].append(new_node)

        # 2. ATTACHED_TO 엣지 생성 (IGW -> VPC)
        vpc_id = attrs.get("attached_vpc_id")
        if vpc_id:
            graph_data["edges"].append({
                "id": f"edge:{res_id}:ATTACHED_TO:{vpc_id}",
                "relation": "ATTACHED_TO",
                "src": target_node_id,
                "src_label": f"internet_gateway:{node.get('name')}",
                "dst": f"{account_id}:{region}:vpc:{vpc_id}",
                "dst_label": f"vpc:{node.get('name')}",
                "directed": True,
                "conditions": [
                    {
                        "key": "state",
                        "value": attrs.get("state", "available")
                    }
                ]
            })

    return graph_data
