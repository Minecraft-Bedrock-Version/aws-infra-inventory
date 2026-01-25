from __future__ import annotations

import botocore
from typing import Any, Dict, List
from datetime import datetime, timezone


def collect_sqs(session, region: str) -> Dict[str, Any]:
    
    # 클라이언트 생성 및 시간 기록
    client = session.client("sqs", region_name="us-east-1")
    collected_at = datetime.now(timezone.utc).isoformat()

    queue_urls: List[str] = []
    raw_list_queues: List[Dict[str, Any]] = []

    # 1. queue 목록
    next_token = None
    while True:
        kwargs = {}
        if next_token:
            kwargs["NextToken"] = next_token
				
        resp = client.list_queues(**kwargs)
        raw_list_queues.append(resp)

        queue_urls.extend(resp.get("QueueUrls", []))

        next_token = resp.get("NextToken")
        if not next_token:
            break

    raw_get_queue_attributes: Dict[str, Any] = {}
    raw_list_queue_tags: Dict[str, Any] = {}

    for url in queue_urls:
        try:
            attrs_resp = client.get_queue_attributes(
                QueueUrl=url,
                AttributeNames=["All"]
            )
            raw_get_queue_attributes[url] = attrs_resp
        except botocore.exceptions.ClientError as e:
            raw_get_queue_attributes[url] = {"__error__": _err(e)}

        try:
            tags_resp = client.list_queue_tags(QueueUrl=url)
            raw_list_queue_tags[url] = tags_resp
        except botocore.exceptions.ClientError as e:
            raw_list_queue_tags[url] = {"__error__": _err(e)}

    return {
        "service": "sqs",
        "region": region,
        "collected_at": collected_at,
        "raw": {
            "list_queues": raw_list_queues,
            "get_queue_attributes": raw_get_queue_attributes,
            "list_queue_tags": raw_list_queue_tags,
        },
    }


def _err(e: Exception) -> Dict[str, Any]:
    if hasattr(e, "response"):
        r = getattr(e, "response", {}) or {}
        return {
            "Error": r.get("Error", {}),
            "ResponseMetadata": r.get("ResponseMetadata", {}),
        }
    return {"Error": {"Message": str(e)}}