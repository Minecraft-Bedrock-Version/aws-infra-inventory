import json
from typing import Any, Dict, List

# 1. EC2 및 KeyPair 데이터를 그래프 데이터(Nodes, Edges)로 변환
def transform_ec2_to_graph(ec2_normalized_data: Dict[str, Any]) -> Dict[str, Any]:

    graph_data = {
        "schema_version": "1.0",
        "collected_at": ec2_normalized_data.get("collected_at"),
        "account_id": ec2_normalized_data.get("account_id"),
        "nodes": [],
        "edges": []
    }

    account_id = ec2_normalized_data.get("account_id")
    
    # KeyPair ID 매핑을 위한 임시 저장소 (EC2 연결용)
    key_name_to_node_id = {}
    for node in ec2_normalized_data.get("nodes", []):
        if node["node_type"] == "key_pair":
            key_name_to_node_id[node["name"]] = node["node_id"]

    # 노드 및 엣지 생성 루프
    for node in ec2_normalized_data.get("nodes", []):
        n_type = node["node_type"]
        n_id = node["node_id"]
        res_id = node["resource_id"]
        region = node.get("region")
        attrs = node.get("attributes", {})

        # 1-1. EC2 Instance 노드 및 관련 엣지 처리
        if n_type == "ec2_instance":
            new_node = {
                "id": n_id,
                "type": "ec2_instance",
                "name": node.get("name"),
                "arn": f"arn:aws:ec2:{region}:{account_id}:instance/{res_id}",
                "region": region,
                "properties": {
                    "instance_type": attrs.get("instance_type"),
                    "state": attrs.get("state"),
                    "networking": {
                        "public_ip": attrs.get("public_ip"),
                        "private_ip": attrs.get("private_ip"),
                        "is_public": attrs.get("public", False)
                    },
                    "iam_instance_profile": attrs.get("iam_instance_profile"),
                    "ssh_key_name": attrs.get("key_name"),
                    "discovered_endpoints": {
                        "sqs_url": attrs.get("sqs_info", {}).get("queue_url"),
                        "rds_endpoint": attrs.get("rds_info", {}).get("db_endpoint")
                    },
                    "launch_time": attrs.get("launch_time")
                }
            }
            graph_data["nodes"].append(new_node)

            # [Edge] USES_KEY: 인스턴스와 키 페어 연결
            key_name = attrs.get("key_name")
            if key_name and key_name in key_name_to_node_id:
                target_key_id = key_name_to_node_id[key_name]
                graph_data["edges"].append({
                    "id": f"edge:{res_id}:USES_KEY:{key_name}",
                    "relation": "USES_KEY",
                    "src": n_id,
                    "src_label": f"ec2_instance:{node.get('name')}",
                    "dst": target_key_id,
                    "dst_label": f"key_pair:{key_name}",
                    "directed": True,
                    "conditions": ["ec2:DescribeInstances", "ec2:DescribeKeyPairs"]
                })

            # [Edge] MEMBER_OF: 인스턴스와 VPC 연결
            vpc_id = attrs.get("vpc_id")
            if vpc_id:
                graph_data["edges"].append({
                    "id": f"edge:{res_id}:MEMBER_OF:{vpc_id}",
                    "relation": "MEMBER_OF",
                    "src": n_id,
                    "src_label": f"ec2_instance:{node.get('name')}",
                    "dst": f"{account_id}:{region}:vpc:{vpc_id}",
                    "dst_label": f"vpc:{vpc_id}",
                    "directed": True,
                    "conditions": ["ec2:DescribeNetworkInterfaces"]
                })

            # [Edge] ACCESS_TO: UserData에서 탐지된 SQS 연결
            sqs_info = attrs.get("sqs_info", {})
            if sqs_info.get("detected"):
                q_url = sqs_info.get("queue_url", "")
                q_name = q_url.split("/")[-1] if q_url else "unknown"
                graph_data["edges"].append({
                    "id": f"edge:{res_id}:ACCESS_TO:{q_name}",
                    "relation": "ACCESS_TO",
                    "src": n_id,
                    "src_label": f"ec2_instance:{node.get('name')}",
                    "dst": f"{account_id}:{region}:sqs:{q_name}",
                    "dst_label": f"sqs:{q_name}",
                    "directed": True,
                    "conditions": ["sqs:SendMessage", "sqs:ReceiveMessage"]
                })

        # 1-2. Key Pair 노드 처리
        elif n_type == "key_pair":
            new_node = {
                "id": n_id,
                "type": "key_pair",
                "name": node.get("name"),
                "arn": f"arn:aws:ec2:{region}:{account_id}:key-pair/{node.get('name')}",
                "region": region,
                "properties": {
                    "key_type": attrs.get("key_type"),
                    "key_fingerprint": attrs.get("key_fingerprint"),
                    "tags": attrs.get("tags", {})
                }
            }
            graph_data["nodes"].append(new_node)

    return graph_data
