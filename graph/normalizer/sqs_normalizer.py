from __future__ import annotations
import json as json_lib
from typing import Any, Dict, List
from datetime import datetime, timezone


# 1. SQS 리소스 데이터 정규화
def normalize_sqs(collected: Dict[str, Any], account_id: str) -> Dict[str, Any]:
    region = collected.get("region")
    collected_at = collected.get("collected_at")
    
    raw_attrs_map = collected.get("raw", {}).get("get_queue_attributes", {})
    raw_tags_map = collected.get("raw", {}).get("list_queue_tags", {})

    nodes: List[Dict[str, Any]] = []

    for queue_url, attrs_resp in raw_attrs_map.items():
        if "__error__" in attrs_resp:
            continue
            
        attrs = attrs_resp.get("Attributes", {})
        tags = raw_tags_map.get(queue_url, {}).get("Tags", {})
        
        queue_arn = attrs.get("QueueArn")
        queue_name = _queue_name_from_url(queue_url)
        node_id = f"{account_id}:{region}:sqs:{queue_name}"

        # DLQ(Dead Letter Queue) 타겟 ARN 추출
        redrive_policy = attrs.get("RedrivePolicy")
        dlq_arn = None
        if redrive_policy:
            try:
                dlq_arn = json_lib.loads(redrive_policy).get("deadLetterTargetArn")
            except Exception:
                pass

        # 노드 데이터 구조 생성
        node = {
            "node_type": "sqs",
            "node_id": node_id,
            "resource_id": queue_name,
            "name": tags.get("Name", queue_name),
            "account_id": account_id,
            "region": region,

            # 큐 세부 속성 (제한 시간, 메시지 크기, 보안 설정 등)
            "attributes": {
                "queue_url": queue_url,
                "visibility_timeout": _int(attrs.get("VisibilityTimeout")),
                "max_message_size": _int(attrs.get("MaximumMessageSize")),
                "message_retention_period": _int(attrs.get("MessageRetentionPeriod")),
                "delay_seconds": _int(attrs.get("DelaySeconds")),
                "receive_wait_time_seconds": _int(attrs.get("ReceiveMessageWaitTimeSeconds")),
                "sse_enabled": _bool(attrs.get("SqsManagedSseEnabled") or attrs.get("KmsMasterKeyId")),
                "approximate_messages": _int(attrs.get("ApproximateNumberOfMessages")),
                "created_timestamp": _int(attrs.get("CreatedTimestamp")),
                "last_modified_timestamp": _int(attrs.get("LastModifiedTimestamp")),
                "policy": attrs.get("Policy"), 
            },

            # 관계 정보 (ARN, KMS 키, DLQ 연결)
            "relationships": {
                "queue_arn": queue_arn,
                "kms_key_id": attrs.get("KmsMasterKeyId"), 
                "dead_letter_queue_arn": dlq_arn 
            },

            # 데이터 원천 정보
            "raw_refs": {
                "source": ["list_queues", "get_queue_attributes(All)"],
                "collected_at": collected_at,
            },
        }
        nodes.append(node)

    return {
        "schema_version": "1.0",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "account_id": account_id,
        "nodes": nodes,
    }


# 2. 유틸리티 함수 
def _queue_name_from_url(queue_url: str) -> str:
    return queue_url.rstrip("/").split("/")[-1]


def _int(v: Any) -> int | None:
    if v is None: 
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _bool(v: Any) -> bool:
    """값 불리언 변환 및 문자열 처리"""
    if v is None: 
        return False
    if isinstance(v, bool): 
        return v
    if isinstance(v, str): 
        return v.lower() == "true"
    return bool(v)


# 3. 로컬 테스트 실행부
if __name__ == "__main__":
    sample_collected = {
        "region": "us-east-1",
        "collected_at": "2026-01-16T05:54:06Z",
        "raw": {
            "get_queue_attributes": {
                "https://sqs.us-east-1.amazonaws.com/288528695623/cash_charging_queue": {
                    "Attributes": {
                        "QueueArn": "arn:aws:sqs:us-east-1:288528695623:cash_charging_queue",
                        "VisibilityTimeout": "30",
                        "SqsManagedSseEnabled": "true",
                        "CreatedTimestamp": "1768454340"
                    }
                }
            },
            "list_queue_tags": {
                "https://sqs.us-east-1.amazonaws.com/288528695623/cash_charging_queue": {
                    "Tags": {"Name": "charging-queue"}
                }
            }
        }
    }
    
    result = normalize_sqs(sample_collected, "288528695623")
    print(json_lib.dumps(result, indent=2))
