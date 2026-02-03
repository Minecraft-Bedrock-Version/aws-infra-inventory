from __future__ import annotations
from typing import Any, Dict

def normalize_lambda(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    functions = raw_payload.get("functions", [])
    nodes = []

    # Lambda Function 노드
    for function_value in functions:
        environment = function_value.get("Environment")
        event_source_mapping = function_value.get("EventSourceMappings", [])
            
        node_type = "lambda"
        name = function_value.get("FunctionName")
        node_id = f"{account_id}:{region}:{node_type}:{name}"
        runtime = function_value.get("Runtime")
        handler = function_value.get("Handler")
        code_size = function_value.get("CodeSize")
        timeout = function_value.get("Timeout")
        memory_size = function_value.get("MemorySize")
        environment_variables = environment.get("Variables")
        last_modified = function_value.get("LastModified")
        event_source_arn = event_source_mapping[0].get("EventSourceArn")
        
        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": name,
            "name": name,
            "account_id": account_id,
            "region": region,
            "attributes": {
                "runtime": runtime,
                "handler": handler,
                "code_size": code_size,
                "timeout": timeout,
                "memory_size":memory_size,
                "environment_variables": environment_variables,
                "last_modified": last_modified
            },
            "event_source_mapping": {
                "event_source_arn": event_source_arn
            }
        }

        nodes.append(node)

    return nodes
