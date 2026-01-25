import json
from typing import Any, Dict, List

def transform_ec2_to_graph(ec2_normalized_data: Any) -> Dict[str, Any]:
    # 1. [방어 로직] 문자열 데이터 역직렬화 및 타입 체크
    curr = ec2_normalized_data
    try:
        for _ in range(3):
            if isinstance(curr, (str, bytes)):
                curr = json.loads(curr)
            else:
                break
    except Exception:
        return {"nodes": [], "edges": []}

    if not isinstance(curr, dict):
        return {"nodes": [], "edges": []}

    # 2. [구조 보정] 중첩된 {'nodes': {'nodes': [...]}} 구조 대응
    outer_nodes = curr.get("nodes", {})
    if isinstance(outer_nodes, dict):
        nodes_payload = outer_nodes.get("nodes", [])
        account_id = outer_nodes.get("account_id", curr.get("account_id", "288528695623"))
    else:
        nodes_payload = outer_nodes if isinstance(outer_nodes, list) else []
        account_id = curr.get("account_id", "288528695623")

    graph_data = {
        "schema_version": "1.0",
        "collected_at": curr.get("collected_at") if isinstance(curr, dict) else None,
        "account_id": account_id,
        "nodes": [],
        "edges": []
    }

    # 3. KeyPair ID 매핑을 위한 사전 준비 (중복 순회 방지 및 안전한 접근)
    key_name_to_node_id = {}
    for node in nodes_payload:
        if not isinstance(node, dict): continue
        if str(node.get("node_type")).lower() == "key_pair":
            key_name_to_node_id[node.get("name")] = node.get("node_id")

    # 4. 노드 및 엣지 생성 메인 루프
    for node in nodes_payload:
        if not isinstance(node, dict): continue
        
        n_type = str(node.get("node_type", "")).lower()
        n_id = node.get("node_id")
        res_id = node.get("resource_id")
        region = node.get("region", "us-east-1")
        attrs = node.get("attributes", {})
        rels = node.get("relationships", {})
        name = node.get("name") or res_id

        # 4-1. EC2 Instance 노드 처리
        if "instance" in n_type:
            # [Linker 핵심] 서브넷 및 IAM 프로파일 정보 추출
            subnet_id = attrs.get("subnet_id") or rels.get("subnet_id")
            iam_profile = attrs.get("iam_instance_profile") or rels.get("iam_instance_profile")
            vpc_id = attrs.get("vpc_id") or rels.get("vpc_id")
            public_ip = attrs.get("public_ip")
            is_public = public_ip is not None

            new_node = {
                "id": n_id,
                "type": "ec2_instance",
                "name": name,
                "arn": f"arn:aws:ec2:{region}:{account_id}:instance/{res_id}",
                "region": region,
                "properties": {
                    "instance_type": attrs.get("instance_type"),
                    "state": attrs.get("state"),
                    "public_ip": public_ip,
                    "private_ip": attrs.get("private_ip"),
                    "subnet_id": subnet_id,    # Linker가 Subnet과 연결할 때 사용
                    "iam_profile": iam_profile, # Linker가 IAM Role과 연결할 때 사용
                    "public": is_public,       # Linker가 IGW와 연결할 때 사용
                    "vpc_id": vpc_id           # Linker가 IGW와 연결할 때 사용
                }
            }
            graph_data["nodes"].append(new_node)

            # [Edge] USES_KEY: 인스턴스와 키 페어 연결
            key_name = attrs.get("key_name")
            if key_name and key_name in key_name_to_node_id:
                graph_data["edges"].append({
                    "id": f"edge:{res_id}:USES_KEY:{key_name}",
                    "relation": "USES_KEY",
                    "src": n_id,
                    "dst": key_name_to_node_id[key_name],
                    "directed": True
                })

            # [Edge] MEMBER_OF: VPC 연결
            vpc_id = attrs.get("vpc_id") or rels.get("vpc_id")
            if vpc_id:
                graph_data["edges"].append({
                    "id": f"edge:{res_id}:MEMBER_OF:{vpc_id}",
                    "relation": "MEMBER_OF",
                    "src": n_id,
                    "dst": f"{account_id}:{region}:vpc:{vpc_id}",
                    "directed": True
                })

            # [Edge] CONNECTS_TO_RDS: EC2가 RDS를 감지한 경우
            rds_info = attrs.get("rds_info", {})
            if isinstance(rds_info, dict) and rds_info.get("detected"):
                # EC2의 rds_info에는 RDS의 node_id가 포함되어야 함
                rds_node_id = rds_info.get("node_id")
                if rds_node_id:
                    graph_data["edges"].append({
                        "id": f"edge:{res_id}:CONNECTS_TO_RDS:{rds_node_id}",
                        "relation": "CONNECTS_TO_RDS",
                        "src": n_id,
                        "dst": rds_node_id,
                        "directed": False,
                        "conditions": [
                            {
                                "ec2": {
                                    "attributes": {
                                        "rds_info": {
                                            "detected": True
                                        }
                                    }
                                }
                            }
                        ]
                    })

            # [Edge] ACCESSES_SQS: EC2가 SQS를 감지한 경우
            sqs_info = attrs.get("sqs_info", {})
            if isinstance(sqs_info, dict) and sqs_info.get("detected"):
                sqs_node_id = sqs_info.get("node_id")
                if sqs_node_id:
                    graph_data["edges"].append({
                        "id": f"edge:{res_id}:ACCESSES_SQS:{sqs_node_id}",
                        "relation": "ACCESSES_SQS",
                        "src": n_id,
                        "dst": sqs_node_id,
                        "directed": True,
                        "conditions": [
                            {
                                "ec2": {
                                    "attributes": {
                                        "sqs_info": {
                                            "detected": True
                                        }
                                    }
                                }
                            }
                        ]
                    })

            # [Edge] CONNECTED_TO_IGW: EC2가 public이고 IGW가 있는 경우
            igw_info = attrs.get("igw_info", {})
            if isinstance(igw_info, dict) and igw_info.get("detected"):
                igw_node_id = igw_info.get("node_id")
                if igw_node_id:
                    graph_data["edges"].append({
                        "id": f"edge:{res_id}:CONNECTED_TO_IGW:{igw_node_id}",
                        "relation": "CONNECTED_TO_IGW",
                        "src": n_id,
                        "dst": igw_node_id,
                        "directed": False,
                        "conditions": [
                            {
                                "ec2": {
                                    "attributes": {
                                        "public": True
                                    }
                                }
                            }
                        ]
                    })

        # 4-2. Key Pair 노드 처리
        elif "key" in n_type:
            graph_data["nodes"].append({
                "id": n_id,
                "type": "key_pair",
                "name": name,
                "region": region,
                "properties": {
                    "key_type": attrs.get("key_type"),
                    "key_fingerprint": attrs.get("key_fingerprint")
                }
            })

    return graph_data