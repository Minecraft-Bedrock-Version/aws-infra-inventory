# collectors/sqs_collector.py
from __future__ import annotations

import botocore
from typing import Any, Dict, List

DEFAULT_ATTRS = [
    "QueueArn",
    "Policy",
    "VisibilityTimeout",
    "MaximumMessageSize",
    "MessageRetentionPeriod",
    "DelaySeconds",
    "ReceiveMessageWaitTimeSeconds",
    "RedrivePolicy",
    "KmsMasterKeyId",
    "KmsDataKeyReusePeriodSeconds",
    "SqsManagedSseEnabled",
    "FifoQueue",
    "ContentBasedDeduplication",
]


def collect_sqs(session, region: str) -> Dict[str, Any]:
    client = session.client("sqs", region_name=region)

    queues: List[Dict[str, Any]] = []

    # list_queues는 paginator 없음 (NextToken 방식)
    next_token = None
    while True:
        kwargs = {}
        if next_token:
            kwargs["NextToken"] = next_token

        resp = client.list_queues(**kwargs)
        for url in resp.get("QueueUrls", []):
            q: Dict[str, Any] = {"QueueUrl": url, "Attributes": {}, "Tags": {}}

            try:
                attrs = client.get_queue_attributes(QueueUrl=url, AttributeNames=DEFAULT_ATTRS)
                q["Attributes"] = attrs.get("Attributes", {})
            except botocore.exceptions.ClientError as e:
                q["get_queue_attributes_error"] = _err(e)

            # tags (선택)
            try:
                tags = client.list_queue_tags(QueueUrl=url)
                q["Tags"] = tags.get("Tags", {})
            except botocore.exceptions.ClientError as e:
                q["list_queue_tags_error"] = _err(e)

            queues.append(q)

        next_token = resp.get("NextToken")
        if not next_token:
            break

    return {"service": "sqs", "region": region, "queues": queues}


def _err(e: Exception) -> Dict[str, Any]:
    if hasattr(e, "response"):
        r = getattr(e, "response", {}) or {}
        return {"Error": r.get("Error", {}), "ResponseMetadata": r.get("ResponseMetadata", {})}
    return {"Error": {"Message": str(e)}}


if __name__ == "__main__":
    import argparse, boto3, json

    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=None)
    ap.add_argument("--region", default="ap-northeast-2")
    args = ap.parse_args()

    sess = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    data = collect_sqs(sess, args.region)
    print(json.dumps(data, ensure_ascii=False, indent=2))