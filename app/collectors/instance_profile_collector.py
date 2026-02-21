import boto3
import json
from datetime import datetime
from typing import Any, Dict, List

def collect_instance_profiles(session, region: str) -> Dict[str, Any]:
    iam = session.client("iam")
    
    paginator = iam.get_paginator("list_instance_profiles")
    
    profiles: List[Dict[str, Any]] = []

    print("[*] Starting to collect IAM Instance Profiles...")

    try:
        for page in paginator.paginate():
            for profile in page["InstanceProfiles"]:
                profile_name = profile["InstanceProfileName"]
                print(f"[+] Found Profile: {profile_name}")

                profile_info = {
                    "InstanceProfileName": profile_name,
                    "InstanceProfileId": profile["InstanceProfileId"],
                    "Arn": profile["Arn"],
                    "CreateDate": profile["CreateDate"].isoformat(),
                    "Path": profile["Path"],
                    # 이 프로파일에 연결된 Role 리스트
                    "Roles": [
                        {
                            "RoleName": r["RoleName"],
                            "RoleId": r["RoleId"],
                            "Arn": r["Arn"]
                        } for r in profile.get("Roles", [])
                    ]
                }
                profiles.append(profile_info)

    except Exception as e:
        print(f"[-] Error collecting instance profiles: {e}")

    return {
        "region": region, #리전
        "count": len(profiles), #인스턴스 개수
        "instance_profiles": profiles #인스턴스 리스트
    }
