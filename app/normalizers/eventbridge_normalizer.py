import json
from typing import Any, Dict, List

def normalize_eventbridge_rules(raw_payload: Dict[str, Any], account_id: str, region: str) -> List[Dict[str, Any]]:

    eventbridge_data = raw_payload.get("eventbridge", {})
    rules_list = eventbridge_data.get("rules", [])
    
    nodes = []
    
    for rule in rules_list:
        rule_name = rule.get("Name")
        rule_arn = rule.get("Arn")
        node_type = "eventbridge_rule"
        
        #각 필드를 채우기 위한 값
        node_id = f"{account_id}:{region}:{node_type}:{rule_name}"
        event_pattern = rule.get("EventPattern")
        if isinstance(event_pattern, str):
            try:
                event_pattern = json.loads(event_pattern)
            except (json.JSONDecodeError, TypeError):
                pass

        #Targets 정규화
        normalized_targets = []
        for target in rule.get("Targets", []):
            normalized_targets.append({
                "id": target.get("Id"),
                "target_arn": target.get("Arn"),
                "input": target.get("Input"), # 🚨 공격 시나리오 핵심 포인트
                "input_path": target.get("InputPath"),
                "input_transformer": target.get("InputTransformer"),
                "role_arn": target.get("RoleArn")
            })

        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": rule_name,
            "name": rule_name,
            "account_id": account_id,
            "region": region,
            "arn": rule_arn,
            "attributes": {
                "state": rule.get("State"),
                "event_bus_name": rule.get("EventBusName", "default"),
                "event_pattern": event_pattern, # 파싱된 이벤트 패턴
                "targets": normalized_targets,   # 정규화된 타겟 리스트
                "description": rule.get("Description"),
                "tags": rule.get("Tags", [])
            }
        }
        nodes.append(node)
    
    return nodes
