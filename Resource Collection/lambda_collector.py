# collectors/lambda_collector.py
from __future__ import annotations

import botocore
from typing import Any, Dict, List


def collect_lambda(session, region: str) -> Dict[str, Any]:
    client = session.client("lambda", region_name=region)

    functions: List[Dict[str, Any]] = []
    paginator = client.get_paginator("list_functions")

    for page in paginator.paginate():
        for fn in page.get("Functions", []):
            fn_name = fn.get("FunctionName")
            fn_arn = fn.get("FunctionArn")

            item: Dict[str, Any] = {
                "FunctionName": fn_name,
                "FunctionArn": fn_arn,
                "Runtime": fn.get("Runtime"),
                "Role": fn.get("Role"),
                "Handler": fn.get("Handler"),
                "LastModified": fn.get("LastModified"),
                "CodeSize": fn.get("CodeSize"),
                "Timeout": fn.get("Timeout"),
                "MemorySize": fn.get("MemorySize"),
                "Description": fn.get("Description"),
                "PackageType": fn.get("PackageType"),
                "Architectures": fn.get("Architectures"),
                "Environment": fn.get("Environment", {}),
                "VpcConfig": fn.get("VpcConfig", {}),
                "TracingConfig": fn.get("TracingConfig", {}),
                "KMSKeyArn": fn.get("KMSKeyArn"),
                "Layers": fn.get("Layers", []),
                "Tags": {},
                "ResourcePolicy": None,
                "EventSourceMappings": [],
            }

            # get_function (설정/코드 위치 등 조금 더 상세)
            try:
                gf = client.get_function(FunctionName=fn_name)
                item["Configuration"] = gf.get("Configuration", {})
                item["Code"] = gf.get("Code", {})
            except botocore.exceptions.ClientError as e:
                item["get_function_error"] = _err(e)

            # get_policy (리소스 정책; 없으면 ResourceNotFoundException)
            try:
                pol = client.get_policy(FunctionName=fn_name)
                item["ResourcePolicy"] = pol.get("Policy")
            except botocore.exceptions.ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code not in ("ResourceNotFoundException", "ResourceNotFound"):
                    item["get_policy_error"] = _err(e)

            # list_event_source_mappings (SQS/Kinesis/DynamoDB 트리거 등)
            try:
                esm_p = client.get_paginator("list_event_source_mappings")
                mappings = []
                for p in esm_p.paginate(FunctionName=fn_name):
                    mappings.extend(p.get("EventSourceMappings", []))
                item["EventSourceMappings"] = mappings
            except botocore.exceptions.ClientError as e:
                item["event_source_mappings_error"] = _err(e)

            # list_tags (선택)
            try:
                tags = client.list_tags(Resource=fn_arn)
                item["Tags"] = tags.get("Tags", {})
            except botocore.exceptions.ClientError as e:
                item["list_tags_error"] = _err(e)

            functions.append(item)

    return {"service": "lambda", "region": region, "functions": functions}


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
    data = collect_lambda(sess, args.region)
    print(json.dumps(data, ensure_ascii=False, indent=2))