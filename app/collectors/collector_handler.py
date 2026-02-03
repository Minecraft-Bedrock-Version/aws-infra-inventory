from datetime import datetime, timezone
import boto3

from collectors.ec2_collectors import collect_ec2
from collectors.lambda_collectors import collect_lambda
from collectors.iam_user_collectors import collect_iam_user
from collectors.iam_role_collectors import collect_iam_role
from collectors.sqs_collectors import collect_sqs
from collectors.rds_collectors import collect_rds
from collectors.network_collectors import collect_network

def handler(event, session):
    #event(payload)에서 계정 id, region을 받아옴
    account_id = event["account_id"]
    region = event["region"]

    #시간 기록
    collected_at = event.get(
        "collected_at",
        datetime.now(timezone.utc).isoformat()
    )

    #최종적으로 반환될 딕셔너리 구조
    result = {
        "account_id": account_id, #계정 id
        "region": region, #리전
        "collected_at": collected_at, #시간
        #추가적으로 아래에 호출된 서비스들의 내용을 담음
    }

    #딕셔너리에 추가될 서비스 리스트들
    result["ec2"] = collect_ec2(session, region)
    result["lambda"] = collect_lambda(session, region)
    result["iam_user"] = collect_iam_user(session)
    result["iam_role"] = collect_iam_role(session)
    result["sqs"] = collect_sqs(session, region)
    result["rds"] = collect_rds(session, region)
    network = []
    network = collect_network(session, region)
    result["vpc"] = network["vpc"]
    result["subnet"] = network["subnet"]
    result["igw"] = network["igw"]
    result["route_table"] = network["route_table"]

    return result