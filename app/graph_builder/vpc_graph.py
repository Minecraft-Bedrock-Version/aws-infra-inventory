import re
from typing import Dict, List, Any

def transform_vpc_to_graph(normalized_data):
    graph_data = {
        "schema_version": "1.0",
        "collected_at": normalized_data["collected_at"],
        "account_id": normalized_data["account_id"],
        "nodes": [],
        "edges": []
    }

    account = normalized_data["account_id"]
    
    for node in normalized_data["nodes"]:
        node_id = node["node_id"]
        region = node_id.split(":")[1]
        res_id = node["resource_id"]
        attrs = node.get("attributes", {})

        # 1. Node 생성
        new_node = {
            "id": node_id,
            "type": node["node_type"],
            "name": node.get("name"),
            "arn": f"arn:aws:ec2:{region}:{account}:{node['node_type']}/{res_id}",
            "region": region,
            "properties": {
                "cidr_block": attrs.get("cidr"),
                "default": attrs.get("default"),
                "internet_gateway_id": attrs.get("internet_gateway_id"),
                # 추가적인 기본값 설정
                "state": "available",
                "instance_tenancy": "default",
                "dns_settings": {"enable_dns_support": True, "enable_dns_hostnames": True}
            }
        }
        graph_data["nodes"].append(new_node)

        # 2. Edge 추론 (VPC - IGW 관계)
        igw_id = attrs.get("internet_gateway_id")
        if igw_id:
            src_node_id = f"{account}:{region}:internet_gateway:{igw_id}"
            edge = {
                "id": f"edge:{igw_id}:ATTACHED_TO:{res_id}",
                "relation": "ATTACHED_TO",
                "src": src_node_id,
                "src_label": f"internet_gateway:{node.get('name')}",
                "dst": node_id,
                "dst_label": f"vpc:{node.get('name')}",
                "directed": True,
                "conditions": []
            }
            graph_data["edges"].append(edge)

    return graph_data