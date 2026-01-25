from datetime import datetime, timezone
import boto3

from app.collectors.iam_user_collectors import collect_iam_users
from app.collectors.iam_role_collectors import collect_iam_roles
from app.collectors.network_collectors import collect_network
from app.collectors.ec2_collectors import collect_ec2
from app.collectors.rds_collectors import collect_rds
from app.collectors.sqs_collectors import collect_sqs
from app.collectors.lambda_collectors import collect_lambda


def handler(event, context):

    # 1. 실행 파라미터
    account_id = event["account_id"]
    region = event["region"]

    collected_at = event.get(
        "collected_at",
        datetime.now(timezone.utc).isoformat()
    )

    session = boto3.Session()

    # 2. 결과 컨테이너
    result = {
        "account_id": account_id,
        "region": region,
        "collected_at": collected_at,
    }

    # IAM (Global)
    result["iam_users"] = collect_iam_users(session)
    result["iam_roles"] = collect_iam_roles(session)

    # Network (여기 안에 vpcs, subnets, igws, route_tables가 들어있음)
    result["network"] = collect_network(session, region)

    # Compute / DB / Messaging
    result["ec2"] = collect_ec2(session, region)
    result["rds"] = collect_rds(session, region)
    result["sqs"] = collect_sqs(session, region)
    result["lambda"] = collect_lambda(session, region)

    return result