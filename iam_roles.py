import boto3
import json
from datetime import datetime
from botocore.exceptions import ClientError

iam = boto3.client("iam")


def datetime_handler(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type not serializable: {type(obj)}")


def collect_all_roles():
    def strip_metadata(d):
        if isinstance(d, dict):
            d.pop("ResponseMetadata", None)
            d.pop("IsTruncated", None)
        return d

    """
    Collect ALL IAM roles with RAW responses,
    and print ONE JSON object to stdout for all.py to consume.
    """
    result = {
        "Roles": [],
        "Errors": [],
    }

    paginator = iam.get_paginator("list_roles")

    try:
        for page in paginator.paginate():
            # keep RAW page content style similar to iam_users
            for role in page.get("Roles", []):
                role_name = role.get("RoleName")
                role_entry = {}

                try:
                    # RAW role info
                    role_entry["Role"] = strip_metadata(role.copy())

                    # Inline role policies (names only, RAW)
                    role_entry["RoleInlinePolicies"] = strip_metadata(
                        iam.list_role_policies(RoleName=role_name)
                    )

                    # Attached managed role policies (RAW)
                    role_entry["RoleAttachedManagedPolicies"] = strip_metadata(
                        iam.list_attached_role_policies(RoleName=role_name)
                    )

                except ClientError as e:
                    role_entry["Error"] = e.response.get("Error", {})
                except Exception as e:
                    role_entry["Error"] = {
                        "Code": type(e).__name__,
                        "Message": str(e),
                    }

                result["Roles"].append(role_entry)

    except ClientError as e:
        result["Errors"].append(e.response.get("Error", {}))
    except Exception as e:
        result["Errors"].append({
            "Code": type(e).__name__,
            "Message": str(e),
        })

    return result


roles_data = collect_all_roles()

# IMPORTANT: print ONLY ONE JSON object to stdout
print(json.dumps(roles_data, indent=4, default=datetime_handler))
