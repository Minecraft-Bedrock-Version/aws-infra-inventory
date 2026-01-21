from __future__ import annotations

import botocore
from typing import Any, Dict, List
from datetime import datetime, timezone

def collect_iam_users():
    iam = boto3.client("iam")

    users_raw = []
    policy_content_cache = {}

    # Managed Policy 내용 수집 및 캐싱
    def get_cached_policy_statement(policy_arn, api_sources):
    
        if policy_arn in policy_content_cache:
            return policy_content_cache[policy_arn]

        try:
            # 정책 정보 및 기본 버전 확인
            p_info = iam.get_policy(PolicyArn=policy_arn)
            v_id = p_info["Policy"]["DefaultVersionId"]

            # 정책 상세 내용(버전) 확인
            p_ver = iam.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=v_id
            )

            api_sources.extend(["iam:GetPolicy", "iam:GetPolicyVersion"])
            statement = p_ver["PolicyVersion"]["Document"].get("Statement", [])

            policy_content_cache[policy_arn] = statement
            return statement
        except Exception:
            return []

    # 수집
    paginator = iam.get_paginator("list_users")

    for page in paginator.paginate():
        for user in page["Users"]:
            user_name = user["UserName"]
            user_id = user["UserId"]

            api_sources = ["iam:ListUsers"]
            attached_policies = []
            inline_policies = []
            group_policies = []

            try:
                # 1. Attached Policy
                attached = iam.list_attached_user_policies(UserName=user_name)
                api_sources.append("iam:ListAttachedUserPolicies")

                for p in attached["AttachedPolicies"]:
                    statement = get_cached_policy_statement(p["PolicyArn"], api_sources)
                    attached_policies.append({
                        "policy_name": p["PolicyName"],
                        "policy_arn": p["PolicyArn"],
                        "statement": statement
                    })

                # 2. Inline Policies 
                inline = iam.list_user_policies(UserName=user_name)
                api_sources.append("iam:ListUserPolicies")

                for p_name in inline["PolicyNames"]:
                    p_detail = iam.get_user_policy(
                        UserName=user_name,
                        PolicyName=p_name
                    )
                    api_sources.append("iam:GetUserPolicy")

                    inline_policies.append({
                        "policy_name": p_name,
                        "statement": p_detail["PolicyDocument"].get("Statement", [])
                    })

                # 3. Group Policies
                groups = iam.list_groups_for_user(UserName=user_name)
                api_sources.append("iam:ListGroupsForUser")

                for g in groups["Groups"]:
                    g_name = g["GroupName"]

                    # 3-1. 그룹 Managed Policies
                    g_attached = iam.list_attached_group_policies(GroupName=g_name)
                    api_sources.append("iam:ListAttachedGroupPolicies")

                    for gp in g_attached["AttachedPolicies"]:
                        statement = get_cached_policy_statement(gp["PolicyArn"], api_sources)
                        group_policies.append({
                            "group_name": g_name,
                            "policy_type": "Managed",
                            "policy_name": gp["PolicyName"],
                            "statement": statement
                        })

                    # 3-2. 그룹 Inline Policies
                    g_inline = iam.list_group_policies(GroupName=g_name)
                    api_sources.append("iam:ListGroupPolicies")

                    for gp_name in g_inline["PolicyNames"]:
                        gp_detail = iam.get_group_policy(
                            GroupName=g_name,
                            PolicyName=gp_name
                        )
                        api_sources.append("iam:GetGroupPolicy")

                        group_policies.append({
                            "group_name": g_name,
                            "policy_type": "Inline",
                            "policy_name": gp_name,
                            "statement": gp_detail["PolicyDocument"].get("Statement", [])
                        })

            except Exception as e:
                print(f"[-] {user_name} 수집 중 에러 발생: {e}")

            # 출력
            users_raw.append({
                "user": user,
                "attached_policies": attached_policies,
                "inline_policies": inline_policies,
                "group_policies": group_policies,
                "api_sources": list(set(api_sources)),
                "collected_at": datetime.now(timezone.utc).isoformat()
            })

    return users_raw
