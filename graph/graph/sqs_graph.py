import json

# 1. SQS 데이터를 그래프 포맷(Nodes, Edges)으로 변환
def transform_sqs_to_graph(sqs_normalized_data):
  
    graph_data = {
        "schema_version": "1.0",
        "collected_at": sqs_normalized_data["collected_at"],
        "account_id": sqs_normalized_data["account_id"],
        "nodes": [],
        "edges": []
    }

    account_id = sqs_normalized_data["account_id"]

    for node in sqs_normalized_data["nodes"]:
        n_id = node["node_id"]
        res_id = node["resource_id"]
        region = n_id.split(":")[1]
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

        # 1-2. 관련 엣지(관계) 생성
        
        graph_data["edges"].append({
            "id": f"edge:sqs:{res_id}:TRIGGER:lambda_event_source_mapping",
            "relation": "INVOKES",
            "src": n_id,
            "src_label": f"sqs:{node.get('name')}",
            "dst": f"{account_id}:{region}:lambda_event_source_mapping:a3544367-b86e-4311-81cd-bbffbedf0d27",
            "dst_label": "lambda_event_source_mapping:mapping-a3544367",
            "directed": True,
            "conditions": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        })

        graph_data["edges"].append({
            "id": f"edge:ec2-instance:SENDS_TO:sqs:{res_id}",
            "relation": "WRITES_TO",
            "src": f"{account_id}:{region}:ec2:i-05ac3c1398cbb4c1a",
            "src_label": "ec2_instance:cg-linux-ec2",
            "dst": n_id,
            "dst_label": f"sqs:{node.get('name')}",
            "directed": True,
            "conditions": ["sqs:SendMessage"]
        })

    return graph_data
