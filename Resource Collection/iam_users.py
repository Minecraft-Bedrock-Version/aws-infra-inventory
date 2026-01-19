import boto3
import json
from datetime import datetime
from botocore.exceptions import ClientError

iam = boto3.client("iam")


def datetime_handler(obj):
    # Match iam_users.py behavior: serialize datetime, fail on unknown types
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type not serializable: {type(obj)}")


def collect_attached_managed_policies_with_documents():
    """
    Collect managed IAM policies that are actually attached (OnlyAttached=True),
    and include each policy's DEFAULT version document.
    Output is ONE JSON object so all.py can capture and save it.
    """
    result = {
        "Policies": [],
        "Errors": [],
    }

    paginator = iam.get_paginator("list_policies")

    try:
        for page in paginator.paginate(Scope="All", OnlyAttached=True):
            for policy in page.get("Policies", []):
                policy_arn = policy.get("Arn")
                if not policy_arn:
                    continue

                try:
                    policy_detail = iam.get_policy(PolicyArn=policy_arn)
                    default_version_id = policy_detail["Policy"]["DefaultVersionId"]

                    policy_version = iam.get_policy_version(
                        PolicyArn=policy_arn,
                        VersionId=default_version_id
                    )

                    result["Policies"].append({
                        "Policy": policy,  # RAW from list_policies
                        "PolicyDetail": policy_detail,  # RAW from get_policy
                        "DefaultVersionId": default_version_id,
                        "PolicyVersion": policy_version,  # RAW from get_policy_version (includes Document)
                    })

                except ClientError as e:
                    result["Errors"].append({
                        "PolicyArn": policy_arn,
                        "Error": e.response.get("Error", {}),
                    })
                except Exception as e:
                    result["Errors"].append({
                        "PolicyArn": policy_arn,
                        "Error": {"Code": type(e).__name__, "Message": str(e)},
                    })

    except ClientError as e:
        # If the whole call fails (e.g., AccessDenied), still print JSON for all.py to save.
        result["Errors"].append({
            "PolicyArn": None,
            "Error": e.response.get("Error", {}),
        })
    except Exception as e:
        result["Errors"].append({
            "PolicyArn": None,
            "Error": {"Code": type(e).__name__, "Message": str(e)},
        })

    return result


policies_data = collect_attached_managed_policies_with_documents()

# IMPORTANT: print ONLY ONE JSON object to stdout (no other prints),
# so all.py can json.loads(stdout) and save iam_policies_<run_id>.json.
print(json.dumps(policies_data, indent=4, default=datetime_handler))
