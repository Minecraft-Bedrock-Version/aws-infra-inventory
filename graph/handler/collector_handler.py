from datetime import datetime, timezone
import boto3

from collectors.iam_user_collectors import collect_iam_users
from collectors.iam_role_collectors import collect_iam_roles
from collectors.network_collectors import collect_ec2_network
from collectors.ec2_collectors import collect_ec2
from collectors.rds_collectors import collect_rds
from collectors.sqs_collectors import collect_sqs
from collectors.lambda_collectors import collect_lambda


def handler(event, context):

    # 실행 파라미터
    account_id = event["account_id"]
    region = event["region"]

    collected_at = event.get(
        "collected_at",
        datetime.now(timezone.utc).isoformat()
    )

    session = boto3.Session()

    # 결과 컨테이너
    result = {
        "account_id": account_id,
        "region": region,
        "collected_at": collected_at,
    }

    # IAM
    result["iam_users"] = collect_iam_users(session)
    result["iam_roles"] = collect_iam_roles(session)

    # Network
    result["network"] = collect_ec2_network(session, region)

    # Compute / DB / Messaging
    result["ec2"] = collect_ec2(session, region)
    result["rds"] = collect_rds(session, region)
    result["sqs"] = collect_sqs(session, region)
    result["lambda"] = collect_lambda(session, region)

    return result
