from __future__ import annotations
from typing import Any, Dict

def normalize_sqs(raw_payload: Dict[str, Any], account_id: str, region: str):
    queues = raw_payload.get("queues", [])
    nodes = []

    #SQS 노드
    for sqs_value in queues:
        attribure = sqs_value.get("Attributes")
        attribure_arn = attribure.get("QueueArn")
        
        node_type = "sqs"
        name = attribure_arn.split(':')[-1]
        node_id = f"{account_id}:{region}:{node_type}:{name}"
        queue_url = sqs_value.get("QueueUrl")
        visibility_timeout =  attribure.get("VisibilityTimeout")
        max_message_size =  attribure.get("MaximumMessageSize")
        message_retention_period =  attribure.get("MessageRetentionPeriod")
        delay_seconds =  attribure.get("DelaySeconds")
        receive_wait_time_seconds =  attribure.get("ReceiveMessageWaitTimeSeconds")
        sse_enabled =  attribure.get("SqsManagedSseEnabled")
        approximate_messages =  attribure.get("ApproximateNumberOfMessages")
        created_timestamp =  attribure.get("CreatedTimestamp")
        last_modified_timestamp =  attribure.get("LastModifiedTimestamp")
        
        node = {
            "node_type": "sqs",
            "node_id": node_id,
            "resource_id": name,
            "name": name,
            "account_id": account_id,
            "region": region,
            "attributes": {
                "queue_url": queue_url,
                "visibility_timeout": visibility_timeout,
                "max_message_size": max_message_size,
                "message_retention_period": message_retention_period,
                "delay_seconds": delay_seconds,
                "receive_wait_time_seconds": receive_wait_time_seconds,
                "sse_enabled": sse_enabled,
                "approximate_messages": approximate_messages,
                "created_timestamp": created_timestamp,
                "last_modified_timestamp": last_modified_timestamp
            }
        }

        nodes.append(node)

    return nodes
