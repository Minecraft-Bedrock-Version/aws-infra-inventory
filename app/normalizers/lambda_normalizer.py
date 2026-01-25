from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime, timezone


def normalize_lambda(
    collected: Dict[str, Any],
    account_id: str,
    region: str,
) -> Dict[str, Any]:

    collected_at = collected["collected_at"]

    raw_list_functions = collected["raw"].get("list_functions", [])
    raw_get_function = collected["raw"].get("get_function", {})
    raw_list_event_source_mappings = collected["raw"].get("list_event_source_mappings", {})
    raw_list_tags = collected["raw"].get("list_tags", {})

    nodes: List[Dict[str, Any]] = []

    # Lambda Function 노드
    for page in raw_list_functions:
        for fn in page.get("Functions", []):
            fn_name = fn.get("FunctionName")
            fn_arn = fn.get("FunctionArn")

            gf = raw_get_function.get(fn_name, {})
            config = gf.get("Configuration", {}) if isinstance(gf, dict) else {}

            tags_resp = raw_list_tags.get(fn_name, {})
            tags = tags_resp.get("Tags", {}) if isinstance(tags_resp, dict) else {}

            vpc_cfg = config.get("VpcConfig", {}) or {}

            node_id = f"{account_id}:{region}:lambda_function:{fn_name}"

            node = {
                "node_type": "lambda_function",

                "node_id": node_id,
                "resource_id": fn_name,
                "name": fn_name,

                "account_id": account_id,
                "region": region,

                "attributes": {
                    "runtime": config.get("Runtime"),
                    "handler": config.get("Handler"),
                    "code_size": config.get("CodeSize"),
                    "timeout": config.get("Timeout"),
                    "memory_size": config.get("MemorySize"),
                    "environment_variables": (config.get("Environment") or {}).get("Variables", {}),
                    "ephemeral_storage_size": (config.get("EphemeralStorage") or {}).get("Size"),
                    "last_modified": config.get("LastModified"),
                },

                "relationships": {
                    "function_arn": fn_arn,
                    "role_arn": config.get("Role"),
                    "vpc_id": vpc_cfg.get("VpcId"),
                    "security_groups": vpc_cfg.get("SecurityGroupIds", []),
                    "subnets": vpc_cfg.get("SubnetIds", []),
                    "log_group": f"/aws/lambda/{fn_name}",
                },

                "raw_refs": {
                    "source": ["list_functions"],
                    "collected_at": collected_at,
                },
            }

            nodes.append(node)

    # Event Source Mapping 노드
    for fn_name, pages in raw_list_event_source_mappings.items():
        if not isinstance(pages, list):
            continue

        for page in pages:
            for esm in page.get("EventSourceMappings", []):
                uuid = esm.get("UUID")
                mapping_arn = esm.get("EventSourceArn")
                target_fn_arn = esm.get("FunctionArn")

                node_id = f"{account_id}:{region}:lambda_event_source_mapping:{uuid}"

                node = {
                    "node_type": "lambda_event_source_mapping",

                    "node_id": node_id,
                    "resource_id": uuid,

                    "account_id": account_id,
                    "region": region,

                    "attributes": {
                        "batch_size": esm.get("BatchSize"),
                        "state": esm.get("State"),
                        "last_modified": esm.get("LastModified"),
                    },

                    "relationships": {
                        "event_source_mapping_arn": f"arn:aws:lambda:{region}:{account_id}:event-source-mapping:{uuid}",
                        "source_sqs": "sqs",
                        "target_function_arn": target_fn_arn,
                    },

                    "raw_refs": {
                        "source": ["list_event_source_mappings"],
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
