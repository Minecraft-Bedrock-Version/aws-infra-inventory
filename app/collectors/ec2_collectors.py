from __future__ import annotations

import botocore
from typing import Any, Dict, List
from datetime import datetime, timezone


def collect_ec2(session, region: str) -> Dict[str, Any]:
		
		# ec2 클라이언트 초기화 및 수집 시간 기록
    client = session.client("ec2", region_name="us-east-1")
    collected_at = datetime.now(timezone.utc).isoformat()
		
		# 데이터를 담을 구조
    raw_instances: List[Dict[str, Any]] = []
    raw_key_pairs: List[Dict[str, Any]] = []
    raw_user_data: Dict[str, Any] = {}

    # 1. describe_instances
    try:
        p = client.get_paginator("describe_instances")
        for page in p.paginate():
            for res in page.get("Reservations", []):
                raw_instances.extend(res.get("Instances", []))
    except botocore.exceptions.ClientError as e:
        return _error_payload("ec2", region, "describe_instances", e)

    # 2. describe_key_pairs
    try:
        # p = client.get_paginator("describe_key_pairs")
        # for page in p.paginate():
        #     raw_key_pairs.extend(page.get("KeyPairs", []))
        resp = client.describe_key_pairs()
        key_pairs = resp.get("KeyPairs", [])
    except botocore.exceptions.ClientError as e:
        raw_key_pairs.append({"__error__": _err(e)})

    # 3. UserData
    for inst in raw_instances:
        iid = inst.get("InstanceId")
        print(f"[+] Processing EC2: {iid}")
        if not iid:
            continue
        try:
            attr = client.describe_instance_attribute(
                InstanceId=iid, Attribute="userData"
            )
            raw_user_data[iid] = attr
        except botocore.exceptions.ClientError as e:
            raw_user_data[iid] = {"__error__": _err(e)}
		
		# 출력
    return {
        "service": "ec2",
        "region": region,
        "collected_at": collected_at,
        "raw": {
            "describe_instances": raw_instances,
            "describe_key_pairs": key_pairs,
            "describe_instance_attribute_userData": raw_user_data,
        },
    }


def _error_payload(service: str, region: str, api: str, e: Exception) -> Dict[str, Any]:
    return {
        "service": service,
        "region": region,
        "error": {"api": api, "detail": _err(e)},
    }


def _err(e: Exception) -> Dict[str, Any]:
    if hasattr(e, "response"):
        r = getattr(e, "response", {}) or {}
        return {
            "Error": r.get("Error", {}),
            "ResponseMetadata": r.get("ResponseMetadata", {}),
        }
    return {"Error": {"Message": str(e)}}