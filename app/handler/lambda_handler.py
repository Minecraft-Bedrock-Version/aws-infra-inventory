import sys
import os
import json 
from datetime import datetime

from app.collectors.collector_handler import handler as run_collectors
from app.collectors.cli_handler import run_cli_collector
from app.normalizers.normalizer_handler import run_normalizers
from app.graph_builder.graph_handler import GraphAssembler
from app.filters.filter_handler import run_filters 
from app.filters.filterling_handler import run_filtering 

def lambda_handler(event, context):
    print("=== LAMBDA START ===")
    print("EVENT:", json.dumps(event, indent=2, ensure_ascii=False))
    cli_input = event.get("cli_input", "")
    account_id = event.get("account_id", "123456789012")
    print("##### CLI Input & Account ID ####")
    print(cli_input, account_id)

    # 데이터 수집 및 정규화
    cli_graph = run_cli_collector(cli_input, account_id)
    print("##### CLI Node ####")
    print(cli_graph)
    # raw_data = run_collectors(event, context)
    # print("##### AWS API ####")
    # print("RAW_DATA KEYS:", raw_data.keys())
    # print("RAW_DATA TYPE:", type(raw_data))
    # normalized_data = run_normalizers(raw_data)
    # print("NORMALIZED KEYS:", normalized_data.keys())
    # print("=== DATA TRACING START ===")
    
    # 1. 수집 단계 (Raw Data) 확인
    raw_data = run_collectors(event, context)
    print(f"1. RAW_DATA 수집 결과:")
    print(f"   - network 키 존재 여부: {'network' in raw_data}")
    if 'network' in raw_data:
        net = raw_data['network']
        print(f"   - VPCs: {len(net.get('vpcs', []))}")
        print(f"   - Subnets: {len(net.get('subnets', []))}")
        print(f"   - IGWs: {len(net.get('internet_gateways', []))}")

    # 2. 정규화 단계 (Normalized Data) 확인
    normalized_data = run_normalizers(raw_data)
    print(f"\n2. NORMALIZED_DATA 결과:")
    for key in ['vpc', 'subnet', 'igw', 'route_table']:
        data = normalized_data.get(key, {})
        # string으로 들어왔을 경우와 dict인 경우 모두 체크
        if isinstance(data, str):
            try: nodes_count = len(json.loads(data).get('nodes', []))
            except: nodes_count = "Error parsing string"
        else:
            nodes_count = len(data.get('nodes', []))
        print(f"   - {key}: {nodes_count} nodes")
    
    print("==== TYPE CHECK AFTER NORMALIZE ====")
    for k, v in normalized_data.items():
        print(f"{k}: {type(v)}")
        if isinstance(v, str):
            print(f"[WARN] {k} is STRING, value preview: {v[:200]}")
    
# 1. resource_map 구성
    resource_map = {}
    for k, v in normalized_data.items():
        if isinstance(v, dict) and "nodes" in v:
            resource_map[k] = v
        elif isinstance(v, str):
            try:
                target_v = json.loads(v)
                if isinstance(target_v, dict) and "nodes" in target_v:
                    resource_map[k] = target_v
            except:
                continue


    # 2. 그래프 조립 및 연결
    assembler = GraphAssembler()
    
    print("--- [DEBUG] Assembler Input Check ---")
    for k, v in resource_map.items():
        print(f"Key: {k:10} | Nodes Count: {len(v.get('nodes', []))}")

    resource_map["account_id"] = account_id 
    
    full_graph = assembler.assemble(resource_map, cli_graph)
    
    if cli_graph.get("nodes"):
        # CLI에서 새로 생성된 노드들의 ID 리스트 추출
        cli_node_ids = {n.get("id") for n in cli_graph["nodes"] if n.get("id")}
        
        # 기존 full_graph 노드 중에서 CLI 노드 ID와 겹치지 않는 것만 남김
        original_nodes = full_graph.get("nodes", [])
        filtered_nodes = [n for n in original_nodes if n.get("id") not in cli_node_ids]
        
        # CLI 노드들을 최종 리스트에 추가 (대체 완료)
        # 만약 assemble 과정에서 이미 추가되었다면, 이 단계에서 "중복 없이" 교체됨을 보장합니다.
        full_graph["nodes"] = filtered_nodes + cli_graph["nodes"]
        
        print(f"DEBUG: 중복 제거 완료. 제거된 노드 수: {len(original_nodes) - len(filtered_nodes)}")
        
    # n['id'] 대신 n.get('id') 사용 및 None 필터링
    all_node_ids = [n.get('id') for n in full_graph.get('nodes', []) if n.get('id')]
    
    print(f"DEBUG: Full Graph Node IDs: {all_node_ids[:40]}... (Total: {len(all_node_ids)})")

    full_graph["account_id"] = account_id # 메타데이터 주입
    print("FULL_GRAPH:", {
        "nodes": len(full_graph.get("nodes", [])),
        "edges": len(full_graph.get("edges", []))
    })
    print("CLI_GRAPH:", cli_graph)
    # # 필터링 및 필드 정제 
    if cli_graph.get("nodes"):
        # CLI에서 입력받은 노드 ID (예: "iam_user:288528695623:scp-test")
        start_id = cli_graph["nodes"][0].get("node_id") or cli_graph["nodes"][0].get("id")
        print(f"DEBUG: 필터링 시작 노드 ID: {start_id}")
        
        # 1. 하위 그래프 추출 (BFS/DFS 알고리즘이 적용된 필터)
        # 여기서 start_id와 연결되지 않은 노드들은 제거되어야 합니다.
        sub_graph = run_filters(full_graph, start_id) 
        
        # 2. 최종 정제 (보안 관계 분석 등)
        if sub_graph.get("nodes") and len(sub_graph["nodes"]) > 0:
            final_ai_graph = run_filtering(sub_graph, start_id)
        else:
            # 연결된 노드가 하나도 없다면 자기 자신(CLI 노드)만이라도 반환
            print("WARN: 연결된 노드가 없습니다. 시작 노드만 반환합니다.")
            final_ai_graph = {
                "schema_version": "1.0",
                "account_id": account_id,
                "nodes": cli_graph["nodes"],
                "edges": []
            }
    else:
        # CLI 입력이 없으면 빈 그래프 반환
        final_ai_graph = { "nodes": [], "edges": [] }
   
    # 지정 경로에 파일 저장
    # target_path = os.path.expanduser("~/ai_web-ui/backend/json/pandyo/search_pandyo.json")
    
    # try:
    #     os.makedirs(os.path.dirname(target_path), exist_ok=True)
    #     with open(target_path, "w", encoding="utf-8") as f:
    #         json.dump(final_ai_graph, f, ensure_ascii=False, indent=2)
    #     save_status = f"Success: File overwritten at {target_path}"
    # except Exception as e:
    #     save_status = f"Fail: {str(e)}"
        
    return {
        "statusCode": 200,
        "body": json.dumps(final_ai_graph)
    }
    
# if __name__ == "__main__":
#     test_event = {
#         "cli_input": "aws iam put-user-policy --user-name scp_test --policy-name cg-sqs-scenario-assumed-role --policy-document '{\"Version\": \"2012-10-17\",\"Statement\": [{\"Effect\": \"Allow\",\"Action\": [\"iam:Get*\",\"iam:List*\"],\"Resource\": \"*\"}]}'",
#         "account_id": "288528695623",
#         "region": "us-east-1"
#     }
#     class MockContext:
#         def __init__(self):
#             self.function_name = "local_test_lambda"
#             self.aws_request_id = "local-uuid-1234"
            
#     result = lambda_handler(test_event, MockContext())
    
#     final_body = json.loads(result["body"])
    
#     with open("local_debug_result.json", "w", encoding="utf-8") as f:
#         json.dump(final_body, f, indent=2, ensure_ascii=False)
#     print("결과가 local_debug_result.json에 저장되었습니다.")