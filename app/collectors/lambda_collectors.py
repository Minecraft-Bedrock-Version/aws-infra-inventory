from __future__ import annotations

import botocore
from typing import Any, Dict, List
from datetime import datetime, timezone


def collect_lambda(session, region: str) -> Dict[str, Any]:
    client = session.client("lambda", region_name="us-east-1")

    collected_at = datetime.now(timezone.utc).isoformat()

    raw_list_functions: List[Dict[str, Any]] = []
    raw_get_function: Dict[str, Any] = {}
    raw_get_policy: Dict[str, Any] = {}
    raw_list_event_source_mappings: Dict[str, Any] = {}
    raw_list_tags: Dict[str, Any] = {}

    paginator = client.get_paginator("list_functions")

    for page in paginator.paginate():
        raw_list_functions.append(page)

        for fn in page.get("Functions", []):
            fn_name = fn.get("FunctionName")
            fn_arn = fn.get("FunctionArn")
            print(f"[+] Processing Lambda: {fn_name}")

            try:
                gf = client.get_function(FunctionName=fn_name)
                raw_get_function[fn_name] = gf
            except botocore.exceptions.ClientError as e:
                raw_get_function[fn_name] = {"__error__": _err(e)}

            try:
                pol = client.get_policy(FunctionName=fn_name)
                raw_get_policy[fn_name] = pol
            except botocore.exceptions.ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code not in ("ResourceNotFoundException", "ResourceNotFound"):
                    raw_get_policy[fn_name] = {"__error__": _err(e)}
                else:
                    raw_get_policy[fn_name] = None

            try:
                esm_p = client.get_paginator("list_event_source_mappings")
                pages = []
                for p in esm_p.paginate(FunctionName=fn_name):
                    pages.append(p)
                raw_list_event_source_mappings[fn_name] = pages
            except botocore.exceptions.ClientError as e:
                raw_list_event_source_mappings[fn_name] = {"__error__": _err(e)}

            try:
                tags = client.list_tags(Resource=fn_arn)
                raw_list_tags[fn_name] = tags
            except botocore.exceptions.ClientError as e:
                raw_list_tags[fn_name] = {"__error__": _err(e)}

    return {
        "service": "lambda",
        "region": region,
        "collected_at": collected_at,
        "raw": {
            "list_functions": raw_list_functions,
            "get_function": raw_get_function,
            "get_policy": raw_get_policy,
            "list_event_source_mappings": raw_list_event_source_mappings,
            "list_tags": raw_list_tags,
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
