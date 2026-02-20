from __future__ import annotations
from typing import Any, Dict, List
import json

def normalize_lambda(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    functions = raw_payload.get("functions", [])
    nodes = []

    # Lambda Function 노드
    for function_value in functions:
        environment = function_value.get("Environment") or {}
        event_source_mappings = function_value.get("EventSourceMappings", [])
    
        node_type = "lambda"
        name = function_value.get("FunctionName")
        node_id = f"{account_id}:{region}:{node_type}:{name}"
        runtime = function_value.get("Runtime")
        handler = function_value.get("Handler")
        code_size = function_value.get("CodeSize")
        timeout = function_value.get("Timeout")
        memory_size = function_value.get("MemorySize")
        environment_variables = environment.get("Variables", {})
        last_modified = function_value.get("LastModified")
        event_source_arns = [
            esm.get("EventSourceArn")
            for esm in event_source_mappings
            if esm.get("EventSourceArn")
        ]
 
        #람다 함수가 사용하는 iam role
        execution_role = function_value.get("ExecutionRole") or function_value.get("Role")

        #소스코드 메타데이터
        raw_code_meta = function_value.get("CodeMetadata") or {}
        code_metadata = {
            "source_url": raw_code_meta.get("SourceUrl"),
            "image_uri": raw_code_meta.get("ImageUri"),
            "handler": raw_code_meta.get("Handler") or function_value.get("Handler"),
            "runtime": raw_code_meta.get("Runtime") or function_value.get("Runtime"),
            "last_modified": raw_code_meta.get("LastModified") or function_value.get("LastModified")
        }

        #리소스 기반 정책
        raw_policy = function_value.get("ResourceBasedPolicy")
        parsed_policy = None
        if raw_policy:
            try:
                parsed_policy = json.loads(raw_policy)
            except (json.JSONDecodeError, TypeError):
                parsed_policy = raw_policy
        
        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": name,
            "name": name,
            "account_id": account_id,
            "region": region,
            "execution_role": execution_role, 
            "code_metadata": code_metadata, 
            "attributes": {
                "runtime": runtime,
                "handler": handler,
                "code_size": code_size,
                "timeout": timeout,
                "memory_size":memory_size,
                "environment_variables": environment_variables,
                "last_modified": last_modified
            },
            "resource_based_policy": parsed_policy, 
            "event_source_mapping": {
                "event_source_arn": [
                    esm.get("EventSourceArn")
                    for esm in event_source_mappings
                    if esm.get("EventSourceArn")
                ]
            }
        }

        nodes.append(node)

    return nodes
