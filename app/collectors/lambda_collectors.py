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

            function["ExecutionRole"] = function.get("Role") 

            #소스 코드 메타데이터 수집
            try:
                #메타데이터(코드 위치, 환경 변수 등) 요청
                detail = lambda_client.get_function(FunctionName=function_name)
                config = detail.get("Configuration", {}) #환경 설정 정보
                code_info = detail.get("Code", {}) #코드 저장소 정보
                env_vars = config.get("Environment", {}).get("Variables", {}) #환경변수
            
                #소스 코드 메타데이터
                function["CodeMetadata"] = {
                    "SourceUrl": code_info.get("Location"), #S3 URL (ZIP 방식일 때)
                    "ImageUri": code_info.get("ImageUri"), #ECR URI (컨테이너 방식일 때)
                    "Handler": config.get("Handler"), #코드 내 실행 시작 함수명
                    "Runtime": config.get("Runtime"), #사용 언어
                    "LastModified": config.get("LastModified"), #마지막 수정일
                    "EnvironmentVariables": env_vars 
                }
            except botocore.exceptions.ClientError as e:
                print(f"[-] Error fetching Detail for {function_name}: {e}")
                function["CodeMetadata"] = None
                
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
