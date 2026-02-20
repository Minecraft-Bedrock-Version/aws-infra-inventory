from __future__ import annotations
from typing import Any, Dict

def graph_eventbridge(raw_payload: Dict[str, Any], account_id: str, region: str) -> list:
    edges = []
    seen_edges = set()
    
    #현재 구현된 서비스들의 node들 모두 미리 불러와두기
    rules = raw_payload.get("eventbridge", {}).get("rules", [])
    
    for rule in rules:
        rule_name = rule.get("Name")
        rule_node_id = f"{account_id}:{region}:eventbridge:{rule_name}"
        targets = rule.get("Targets", []) #Rule에 설정된 타겟 확인
        for target in targets:
            arn = target.get("Arn", "")
            
            #(1) 타겟이 람다인 경우 (EVENTBRIDGE_TRIGGERS_LAMBDA)
            if ":lambda:" in arn:
                lambda_name = arn.split(":")[-1] #함수 이름 추출
                if "/" in lambda_name: # function/name 형태일 경우 대응
                    lambda_name = lambda_name.split("/")[-1]
                
                dst_id = f"{account_id}:{region}:lambda:{lambda_name}"
                edge_id = f"edge:{rule_name}:TRIGGERS:{lambda_name}"
                
                if edge_id not in seen_edges:
                    seen_edges.add(edge_id)
                    edges.append({
                        "id": edge_id,
                        "relation": "EVENTBRIDGE_TRIGGERS_LAMBDA",
                        "src": rule_node_id,
                        "dst": dst_id,
                        "directed": True,
                        "conditions": "Rule triggers this Lambda. Attackers can modify 'Input' to exploit it."
                    })
    return edges
