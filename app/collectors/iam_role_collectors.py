from __future__ import annotations

import botocore
from typing import Any, Dict, List
from datetime import datetime, timezone

# 제외 목록
EXCLUDED_ROLES = {
    "AWSServiceRoleForRDS",
    "AWSServiceRoleForResourceExplorer",
    "AWSServiceRoleForSupport",
    "AWSServiceRoleForTrustedAdvisor",
    "mbvCodebuildRole",
    "mbvEC2Role",
    "mbvLambdaGraphRole",
    "mbvLambdaRole"
}

def collect_iam_roles(session):
    iam = session.client("iam", region_name="us-east-1")
    
    items = []
    policy_content_cache = {}

    # Managed Policy 내용 수집 및 캐싱
    def get_cached_policy_statement(policy_arn, api_sources):
    
        if policy_arn in policy_content_cache:
            return policy_content_cache[policy_arn]

        try:
            # 정책 메타데이터 조회
            p_info = iam.get_policy(PolicyArn=policy_arn)
            v_id = p_info["Policy"]["DefaultVersionId"]

            # 정책 상세 명세 조회
            p_ver = iam.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=v_id
            )

            api_sources.extend([
                "iam:GetPolicy",
                "iam:GetPolicyVersion"
            ])

            statement = p_ver["PolicyVersion"]["Document"].get("Statement", [])
            
            policy_content_cache[policy_arn] = statement
            return statement

        except Exception as e:
            print(f"[-] 정책 조회 실패: {policy_arn} - {e}")
            return []

    # 수집
    paginator = iam.get_paginator("list_roles")

    for page in paginator.paginate():
        for role in page["Roles"]:
            role_name = role["RoleName"]
            
            # 제외 목록 확인
            if role_name in EXCLUDED_ROLES:
                print(f"[!] Skipping excluded role: {role_name}")
                continue

            print(f"[+] Processing Role: {role_name}")

            api_sources = ["iam:ListRoles"]
            attached_policies = []
            inline_policies = []

            try:
                # 1. Attached Policies
                attached_paginator = iam.get_paginator("list_attached_role_policies")
                for a_page in attached_paginator.paginate(RoleName=role_name):
                    api_sources.append("iam:ListAttachedRolePolicies")

                    for p in a_page["AttachedPolicies"]:
                    
                        statement = get_cached_policy_statement(
                            p["PolicyArn"],
                            api_sources
                        )

                        attached_policies.append({
                            "policy_name": p["PolicyName"],
                            "policy_arn": p["PolicyArn"],
                            "statement": statement
                        })
                
                # 2. Inline Policies 
                inline_paginator = iam.get_paginator("list_role_policies")
                for i_page in inline_paginator.paginate(RoleName=role_name):
                    api_sources.append("iam:ListRolePolicies")

                    for p_name in i_page["PolicyNames"]:
                        p_detail = iam.get_role_policy(
                            RoleName=role_name,
                            PolicyName=p_name
                        )
                        api_sources.append("iam:GetRolePolicy")

                        inline_policies.append({
                            "policy_name": p_name,
                            "statement": p_detail["PolicyDocument"].get("Statement", [])
                        })

            except Exception as e:
                print(f"[-] {role_name} 수집 중 에러: {e}")
                continue
						
						# 출력
            items.append({
                "role": role,
                "attached_policies": attached_policies,
                "inline_policies": inline_policies,
                "api_sources": list(set(api_sources)),
                "collected_at": datetime.now(timezone.utc).isoformat()
            })

    return items