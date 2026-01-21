import json
from typing import Any, Dict, List

# 1. SQS 데이터를 노드/엣지 그래프 데이터로 변환
def transform_sqs_to_graph(sqs_normalized_data: Dict[str, Any]) -> Dict[str, Any]:

    graph_data = {
        "schema_version": "1.0",
        "collected_at": sqs_normalized_data.get("collected_at"),
        "account_id": sqs_normalized_data.get("account_id"),
        "nodes": [],
        "edges": []
    }

    account_id = sqs_normalized_data.get("account_id")

    for node in sqs_normalized_data.get("nodes", []):
        n_id = node["node_id"]
        res_id = node["resource_id"]
        region = node["region"]
        attrs = node.get("attributes", {})
        rels = node.get("relationships", {})

        # 1-1. SQS 노드 생성
        new_node = {
            "id": n_id,
            "type": "sqs",
            "name": node.get("name"),
            "arn": rels.get("queue_arn"),
            "region": region,
            "properties": {
                "queue_url": attrs.get("queue_url"),
                "visibility_timeout": attrs.get("visibility_timeout"),
                "max_message_size": attrs.get("max_message_size"),
                "message_retention_period": attrs.get("message_retention_period"),
                "delay_seconds": attrs.get("delay_seconds"),
                "receive_wait_time_seconds": attrs.get("receive_wait_time_seconds"),
                "sse_enabled": attrs.get("sse_enabled", False),
                "approximate_messages": {
                    "available": attrs.get("approximate_number_of_messages", 0),
                    "invisible": attrs.get("approximate_number_of_messages_not_visible", 0),
                    "delayed": attrs.get("approximate_number_of_messages_delayed", 0)
                },
                "timestamps": {
                    "created": attrs.get("created_timestamp"),
                    "last_modified": attrs.get("last_modified_timestamp")
                }
            }
        }
        graph_data["nodes"].append(new_node)

        # 1-2. INVOKES 엣지: SQS가 Lambda 트리거(Mapping)를 호출하는 관계
        mapping_id = "a3544367-b86e-4311-81cd-bbffbedf0d27" 
        graph_data["edges"].append({
            "id": f"edge:sqs:{res_id}:TRIGGER:lambda_mapping",
            "relation": "INVOKES",
            "src": n_id,
            "src_label": f"sqs:{node.get('name')}",
            "dst": f"{account_id}:{region}:lambda_event_source_mapping:{mapping_id}",
            "dst_label": f"lambda_event_source_mapping:mapping-{mapping_id[:8]}",
            "directed": True,
            "conditions": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        })

        # 1-3. WRITES_TO 엣지: 외부 리소스(EC2 등)가 SQS로 데이터를 보내는 관계
        ec2_id = "i-05ac3c1398cbb4c1a"
        graph_data["edges"].append({
            "id": f"edge:ec2:{ec2_id}:SENDS_TO:sqs:{res_id}",
            "relation": "WRITES_TO",
            "src": f"{account_id}:{region}:ec2:{ec2_id}",
            "src_label": f"ec2_instance:cg-linux-ec2",
            "dst": n_id,
            "dst_label": f"sqs:{node.get('name')}",
            "directed": True,
            "conditions": ["sqs:SendMessage"]
        })

        # 1-4. DEAD_LETTER_TO 엣지: 처리 실패 시 DLQ로 이동하는 관계
        dlq_arn = rels.get("dead_letter_queue_arn")
        if dlq_arn:
            dlq_name = dlq_arn.split(":")[-1]
            graph_data["edges"].append({
                "id": f"edge:sqs:{res_id}:DEAD_LETTER_TO:{dlq_name}",
                "relation": "DEAD_LETTER_TO",
                "src": n_id,
                "src_label": f"sqs:{node.get('name')}",
                "dst": f"{account_id}:{region}:sqs:{dlq_name}",
                "dst_label": f"sqs:{dlq_name}",
                "directed": True
            })

    return graph_data
