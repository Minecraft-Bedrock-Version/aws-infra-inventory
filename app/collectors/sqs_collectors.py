from __future__ import annotations
from typing import Any, Dict, List

#SQS
def collect_sqs(session, region: str) -> Dict[str, Any]:
    #API 호출용 객체 생성
    sqs = session.client("sqs", region_name=region)
    paginator = sqs.get_paginator("list_queues")

    #SQS 큐가 저장될 구조 (리스트 안에 딕셔너리가 존재하며, 딕셔너리의 str 키에 어떤 형태로든 값이 들어갈 수 있음)
    queues: List[Dict[str, Any]] = []

    #SQS ListQueues API를 paginator로 반복 호출
    for page in paginator.paginate(): #큐가 많으면 페이지가 넘어가기 때문에 모든 페이지 불러오기
        queue_urls = page.get("QueueUrls", [])
        for queue_url in queue_urls:
            print(f"[+] Processing SQS Queue: {queue_url}")

            #속성값 가져오기
            attributes = sqs.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=["All"]
            ).get("Attributes", {})

            #URL과 속성 묶어서
            queue_info = {
                "QueueUrl": queue_url,
                "Attributes": attributes
            }

            queues.append(queue_info) #최종 저장

    return {
        "region": region, #리전
        "count": len(queues), #큐 개수
        "queues": queues #큐 리스트
    }
