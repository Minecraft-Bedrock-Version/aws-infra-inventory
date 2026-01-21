import json
from typing import Any, Dict, List


# 1. RDS 리소스를 그래프 포맷(Nodes, Edges)으로 변환
def transform_rds_to_graph(rds_normalized_data: Dict[str, Any]) -> Dict[str, Any]:
  
    graph_data = {
        "schema_version": "1.0",
        "collected_at": rds_normalized_data.get("collected_at"),
        "account_id": rds_normalized_data.get("account_id"),
        "nodes": [],
        "edges": []
    }

    account_id = rds_normalized_data.get("account_id")
    nodes_payload = rds_normalized_data.get("nodes", [])

    for node in nodes_payload:
        n_type = node.get("node_type")
        n_id = node.get("node_id")
        res_id = node.get("resource_id")
        region = node.get("region")
        attrs = node.get("attributes", {})
        rels = node.get("relationships", {})

        # 1-1. RDS Instance 노드 및 관련 엣지 처리
        if n_type == "rds_instance":
            new_node = {
                "id": n_id,
                "type": "rds_instance",
                "name": node.get("name"),
                "arn": rels.get("db_instance_arn"),
                "region": region,
                "properties": {
                    "engine": f"{attrs.get('engine')}:{attrs.get('engine_version')}",
                    "endpoint": f"{attrs.get('endpoint_address')}:{attrs.get('endpoint_port')}",
                    "public_access": attrs.get("publicly_accessible", False),
                    "storage_encrypted": attrs.get("storage_encrypted", False),
                    "db_name": attrs.get("db_name"),
                    "instance_class": attrs.get("instance_class"),
                    "status": attrs.get("status")
                }
            }
            graph_data["nodes"].append(new_node)

            # [Edge] MEMBER_OF: VPC 연결
            vpc_id = rels.get("vpc_id")
            if vpc_id:
                graph_data["edges"].append({
                    "id": f"edge:{res_id}:MEMBER_OF:{vpc_id}",
                    "relation": "MEMBER_OF",
                    "src": n_id,
                    "src_label": f"rds_instance:{res_id}",
                    "dst": f"{account_id}:{region}:vpc:{vpc_id}",
                    "dst_label": f"vpc:{vpc_id}",
                    "directed": True,
                    "conditions": ["ec2:DescribeVpcs"]
                })

            # [Edge] USES_SUBNET_GROUP: Subnet Group 연결
            sng_name = rels.get("subnet_group_name")
            if sng_name:
                sng_node_id = f"{account_id}:{region}:rds_subnet_group:{sng_name}"
                graph_data["edges"].append({
                    "id": f"edge:{res_id}:USES_SUBNET_GROUP:{sng_name}",
                    "relation": "USES_SUBNET_GROUP",
                    "src": n_id,
                    "src_label": f"rds_instance:{res_id}",
                    "dst": sng_node_id,
                    "dst_label": f"rds_subnet_group:{sng_name}",
                    "directed": True,
                    "conditions": ["rds:DescribeDBSubnetGroups"]
                })

            # [Edge] ENCRYPTED_BY: KMS 키 연결
            kms_arn = rels.get("kms_key_id")
            if kms_arn:
                # ARN에서 키 UUID 추출
                kms_uuid = kms_arn.split("/")[-1] if "/" in kms_arn else kms_arn.split(":")[-1]
                graph_data["edges"].append({
                    "id": f"edge:{res_id}:ENCRYPTED_BY:{kms_uuid}",
                    "relation": "ENCRYPTED_BY",
                    "src": n_id,
                    "src_label": f"rds_instance:{res_id}",
                    "dst": f"{account_id}:{region}:kms_key:{kms_uuid}",
                    "dst_label": f"kms_key:{kms_uuid[:8]}",
                    "directed": True,
                    "conditions": ["kms:Decrypt", "kms:GenerateDataKey"]
                })

        # 1-2. RDS Subnet Group 노드 및 관련 엣지 처리
        elif n_type == "rds_subnet_group":
            new_node = {
                "id": n_id,
                "type": "rds_subnet_group",
                "name": res_id,
                "arn": rels.get("subnet_group_arn"),
                "region": region,
                "properties": {
                    "status": attrs.get("status"),
                    "subnet_ids": attrs.get("subnets", [])
                }
            }
            graph_data["nodes"].append(new_node)

            # [Edge] CONTAINS: Subnet Group 내 개별 Subnet 연결
            for sub_id in attrs.get("subnets", []):
                graph_data["edges"].append({
                    "id": f"edge:{res_id}:CONTAINS:{sub_id}",
                    "relation": "CONTAINS",
                    "src": n_id,
                    "src_label": f"rds_subnet_group:{res_id}",
                    "dst": f"{account_id}:{region}:subnet:{sub_id}",
                    "dst_label": f"subnet:{sub_id}",
                    "directed": True
                })

    return graph_data
