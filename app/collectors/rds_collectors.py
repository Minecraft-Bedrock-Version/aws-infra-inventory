from __future__ import annotations
from typing import Any, Dict, List

#RDS
def collect_rds(session, region: str) -> Dict[str, Any]:
    #API 호출용 객체 생성
    rds = session.client("rds", region_name=region)
    paginator = rds.get_paginator("describe_db_instances")
    
    #RDS 인스턴스가 저장될 구조 (리스트 안에 딕셔너리가 존재하며, 딕셔너리의 str 키에 어떤 형태로든 값이 들어갈 수 있음)
    instances: List[Dict[str, Any]] = []

    #RDS DescribeDbInstances API를 paginator로 반복 호출
    for page in paginator.paginate(): #인스턴스가 많으면 페이지가 넘어가기 때문에 모든 페이지 불러오기
        db_instances = page.get("DBInstances", [])
        for db in db_instances:
            instance_id = db.get("DBInstanceIdentifier")
            print(f"[+] Processing RDS Instance: {instance_id}")

            instances.append(db) #위에 정의해둔 구조에 인스턴스 딕셔너리를 하나씩 넣음

    return {
        "region": region, #리전
        "count": len(instances), #인스턴스 개수
        "instances": instances #인스턴스 리스트
    }