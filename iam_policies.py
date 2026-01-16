import boto3
import json
from datetime import datetime

def datetime_handler(x):
    if isinstance(x, datetime):
        return x.isoformat()
    return str(x)

# IAM client (global service)
iam_client = boto3.client("iam")

def collect_attached_managed_policies_with_documents():
    """
    Collect all attached managed IAM policies and include their default policy documents.
    """
    results = []

    paginator = iam_client.get_paginator("list_policies")
    for page in paginator.paginate(Scope="All", OnlyAttached=True):
        for policy in page.get("Policies", []):
            policy_arn = policy["Arn"]

            # Get default policy version
            policy_detail = iam_client.get_policy(PolicyArn=policy_arn)
            default_version_id = policy_detail["Policy"]["DefaultVersionId"]

            policy_version = iam_client.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=default_version_id
            )

            results.append({
                "PolicyName": policy["PolicyName"],
                "Arn": policy_arn,
                "DefaultVersionId": default_version_id,
                "Document": policy_version["PolicyVersion"]["Document"],
                "AttachmentCount": policy.get("AttachmentCount"),
                "CreateDate": policy.get("CreateDate"),
                "UpdateDate": policy.get("UpdateDate"),
            })

    return results


def main():
    data = {
        "collected_at": datetime.now().isoformat(),
        "policies": collect_attached_managed_policies_with_documents(),
    }

    print(json.dumps(data, ensure_ascii=False, indent=2, default=datetime_handler))


if __name__ == "__main__":
    main()
