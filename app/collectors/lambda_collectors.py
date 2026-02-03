from __future__ import annotations
from typing import Any, Dict, List
import botocore

#Lambda 함수
def collect_lambda(session, region: str) -> Dict[str, Any]:
    #API 호출용 객체 생성
    lambda_client = session.client("lambda", region_name=region)
    paginator = lambda_client.get_paginator("list_functions")
    
    #함수가 저장될 구조 (리스트 안에 딕셔너리가 존재하며, 딕셔너리의 str 키에 어떤 형태로든 값이 들어갈 수 있음)
    functions: List[Dict[str, Any]] = []

    #Lambda ListFunction API를 paginator로 반복 호출
    for page in paginator.paginate(): #함수가 많으면 페이지가 넘어가기 때문에 모든 페이지 불러오기
        for function in page["Functions"]: #Functions 배열 안에 함수들을 가져옴
            function_name = function["FunctionName"]
            print(f"[+] Processing Lambda Function: {function_name}")
                
            #함수의 리소스 기반 정책 가져오기
            try:
                policy = lambda_client.get_policy(FunctionName=function_name)
                function["ResourceBasedPolicy"] = policy.get("Policy", {})
                
            except botocore.exceptions.ClientError as e: #없을 경우 예외처리
                code = e.response.get("Error", {}).get("Code")
                if code in ("ResourceNotFoundException", "ResourceNotFound"):
                    policy = None
                else:
                    policy = {"__error__": str(e)}
                    
            #이벤트 소스 매핑 (SQS 등 연결된 이벤트가 있는지)
            esm_paginator = lambda_client.get_paginator("list_event_source_mappings")
            event_source_mappings: List[Dict[str, Any]] = []
            try:
                for p in esm_paginator.paginate(FunctionName=function_name):
                    event_source_mappings.extend(p.get("EventSourceMappings", []))
            except botocore.exceptions.ClientError: #없을 경우 예외 처리
                event_source_mappings = []
            function["EventSourceMappings"] = event_source_mappings
            
            functions.append(function) #위에 정의해둔 구조에 함수 딕셔너리를 하나씩 넣음

    return {
        "region": region, #리전
        "count": len(functions), #함수 개수
        "functions": functions #함수 리스트
    }
