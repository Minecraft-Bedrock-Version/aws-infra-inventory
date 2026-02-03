import boto3
import json
from datetime import datetime

from collectors.collector_handler import handler as run_collectors
from collectors.cli_handler import run_cli_collector
from normalizers.normalizer_handler import run_normalizers
from graph_builder.graph_handler import run_graph_builder
from filters.cli_filter import run_cli_filter
from filters.cli_existing import handle_existing_resources
from filters.filterling_handler import run_filtering 

def lambda_handler(event, context):
    region = event.get("region", "us-east-1")
    cli_input = event.get("cli_input", "")
    account_id = event.get("account_id", "")
    
    session = boto3.Session(region_name=region) #전달받은 리전으로 boto3 session 만들어두기
    
    event = { 
        "region": region,
        "cli_input": cli_input,
        "account_id": account_id
    }
    
    #AWS API 호출
    raw_data = run_collectors(event, session)
    
    #Node 정규화
    normalized_data = run_normalizers(raw_data)
    
    #CLI 노드 생성
    cli_graph = run_cli_collector(cli_input, account_id)
    
    #생성된 CLI 노드가 기존에 존재하는 리소스인지, 새로 추가되는 리소스인지 Node ID를 기준으로 판별
    cli_node_filter = run_cli_filter(normalized_data, cli_graph)
    
    if cli_node_filter["existing"]: #기존에 존재하는 Node와 ID가 같다면
        print("existing")
        cli_and_normalized, cli_and_raw_data = handle_existing_resources(cli_node_filter["existing"], normalized_data, raw_data) #덮어쓰기 or Node에 내용 추가 후 Edge 생성으로 넘어갈 예정
        graph_data = run_graph_builder(cli_and_raw_data, cli_and_normalized) #cli raw가 포함된 전체 raw 데이터와 cli node가 포함된 전체 정규화 데이터를 이용해 edge 생성
    if cli_node_filter["new"]: #새롭게 생성되는 리소스라면
        print("new")
        normalized_data["nodes"].extend(cli_node_filter["new"]) #전체 정규화 node에 cli 정규화 node를 포함하여
        graph_data = run_graph_builder(raw_data, normalized_data) #raw data는 기존 raw data만 넘기지만, 정규화 데이터는 cli node가 포함된 값만 넘김
            
    start_node_id = cli_graph["nodes"][0]["node_id"] #cli node의 id를 추출하여 start node id로 지정
    
    filtering_data = run_filtering(graph_data, start_node_id) #start node를 기준으로 직접, 간접 연결된 node, edge만 추출
    
    return filtering_data 

if __name__ == "__main__": #테스트용 실행 코드
    test_event = {
        "cli_input": "aws iam put-user-policy --user-name scp_test --policy-name cg-sqs-scenario-assumed-role --policy-document '{\"Version\": \"2012-10-17\",\"Statement\": [{\"Effect\": \"Allow\",\"Action\": [\"iam:Get*\",\"iam:List*\"],\"Resource\": \"*\"},{\"Effect\": \"Allow\",\"Action\": [\"sts:AssumeRole\"],\"Resource\": \"*\"}]}'",
        "account_id": "288528695623",
        "region": "us-east-1"
    }
    class MockContext:
        def __init__(self):
            self.function_name = "local_test_lambda"
            self.aws_request_id = "local-uuid-1234"
            
    result = lambda_handler(test_event, MockContext())
    
    with open("local_debug_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print("결과가 local_debug_result.json에 저장되었습니다.")