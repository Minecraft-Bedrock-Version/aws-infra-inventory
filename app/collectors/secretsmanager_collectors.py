from __future__ import annotations
from typing import Any, Dict, List

#Secretsmanager
def collect_secretsmanager(session, region) -> Dict[str, Any]:
    #API 호출용 객체 생성
    secretsmanager = session.client("secretsmanager", region_name=region)
    paginator = secretsmanager.get_paginator("list_secrets")
    
    # Secret 정보가 저장될 구조 (리스트 안에 딕셔너리가 존재하며, 딕셔너리의 str 키에 어떤 형태로든 값이 들어갈 수 있음)
    secrets: List[Dict[str, Any]] = []
    
    #Secrets Manager ListSecrets API를 paginator로 반복 호출
    for page in paginator.paginate():
        for secret in page.get("SecretList", []):
            secret_arn = secret.get("ARN")
            print(f"[+] Processing Secret: {secret.get('Name')}")

            #리소스 기반 정책 수집
            policy_res = secretsmanager.get_resource_policy(SecretId=secret_arn)
            
            #최종적으로 리소스 정책 정보 추가
            secret["ResourcePolicy"] = policy_res.get("ResourcePolicy")

            secrets.append(secret) #최종 저장
            
    return {
        "region": region, #리전
        "count": len(secrets), #시크릿 개수
        "secrets": secrets #시크릿 리스트
    }
