from __future__ import annotations
from typing import Any, Dict, List

# EventBridge Rule 및 연결된 Target 수집
def collect_eventbridge(session, region: str) -> Dict[str, Any]:
    #API 호출용 객체 생성
    events = session.client("events")
    paginator = events.get_paginator("list_rules")
    
    rules: List[Dict[str, Any]] = []

    for page in paginator.paginate():
        for rule in page["Rules"]: 
            rule_name = rule["Name"]
                
            print(f"[+] Processing rule: {rule_name}")

            #해당 Rule에 연결된 Target 목록 수집
            targets: List[Dict[str, Any]] = []
            target_list = events.list_targets_by_rule(Rule=rule_name)
            
            for target in target_list.get("Targets", []):
                #Target 상세 정보
                targets.append({
                    "Id": target.get("Id"),
                    "Arn": target.get("Arn"),
                    "Input": target.get("Input"),
                    "InputPath": target.get("InputPath"),
                    "InputTransformer": target.get("InputTransformer"),
                    "RoleArn": target.get("RoleArn")
                })

            #Rule 태그 목록 수집
            try:
                tag_response = events.list_tags_for_resource(ResourceARN=rule["Arn"])
                rule_tags = tag_response.get("Tags", [])
            except Exception:
                rule_tags = []

            # 최종적으로 rule 객체에 Targets와 Tags 정보를 직접 추가 (때려넣기)
            rule["Targets"] = targets
            rule["Tags"] = rule_tags

            # 정보를 확장한 rule 객체를 전체 리스트에 담기
            rules.append(rule)

    return {
        "count": len(rules),
        "rules": rules
    }
