import boto3
import json
from datetime import datetime

def datetime_handler(x):
    if isinstance(x, datetime):
        return x.isoformat()
    raise TypeError("Unknown type")

def get_integrated_user_data():
    iam = boto3.client('iam')
    integrated_users = []

    # 1. 모든 사용자 리스트 가져오기
    paginator = iam.get_paginator('list_users')
    for page in paginator.paginate():
        for user in page['Users']:
            user_name = user['UserName']
            policies_detail = []
            
            try:
                # 사용자에게 직접 연결된 관리형 정책 (Attached Policies)
                attached = iam.list_attached_user_policies(UserName=user_name)
                for p in attached['AttachedPolicies']:
                    p_info = iam.get_policy(PolicyArn=p['PolicyArn'])
                    v_id = p_info['Policy']['DefaultVersionId']
                    p_ver = iam.get_policy_version(PolicyArn=p['PolicyArn'], VersionId=v_id)
                    policies_detail.append({
                        "Source": "Directly Attached",
                        "PolicyName": p['PolicyName'],
                        "PolicyDocument": p_ver['PolicyVersion']['Document']
                    })

                # 사용자에게 직접 작성된 인라인 정책 (Inline Policies)
                inline = iam.list_user_policies(UserName=user_name)
                for p_name in inline['PolicyNames']:
                    p_detail = iam.get_user_policy(UserName=user_name, PolicyName=p_name)
                    policies_detail.append({
                        "Source": "Direct Inline",
                        "PolicyName": p_name,
                        "PolicyDocument": p_detail['PolicyDocument']
                    })

                # 그룹을 통해 상속받은 정책 (Group Policies)
                groups = iam.list_groups_for_user(UserName=user_name)
                for g in groups['Groups']:
                    group_name = g['GroupName']
                    
                    # 그룹에 연결된 관리형 정책
                    g_attached = iam.list_attached_group_policies(GroupName=group_name)
                    for gp in g_attached['AttachedPolicies']:
                        gp_info = iam.get_policy(PolicyArn=gp['PolicyArn'])
                        gv_id = gp_info['Policy']['DefaultVersionId']
                        gv_ver = iam.get_policy_version(PolicyArn=gp['PolicyArn'], VersionId=gv_id)
                        policies_detail.append({
                            "Source": f"Group Attached ({group_name})",
                            "PolicyName": gp['PolicyName'],
                            "PolicyDocument": gv_ver['PolicyVersion']['Document']
                        })
                    
                    # 그룹에 작성된 인라인 정책
                    g_inline = iam.list_group_policies(GroupName=group_name)
                    for gp_name in g_inline['PolicyNames']:
                        gp_detail = iam.get_group_policy(GroupName=group_name, PolicyName=gp_name)
                        policies_detail.append({
                            "Source": f"Group Inline ({group_name})",
                            "PolicyName": gp_name,
                            "PolicyDocument": gp_detail['PolicyDocument']
                        })

            except Exception as e:
                print(f"Error fetching data for {user_name}: {e}")

            # 최종 결과 조립
            integrated_users.append({
                "node_type": "iam_user",
                "name": user_name,
                "resource_id": user['UserId'],
                "attributes": {
                    "arn": user['Arn'],
                    "create_date": user['CreateDate'].isoformat(),
                    "policies": policies_detail
                }
            })

    return integrated_users

if __name__ == "__main__":
    data = get_integrated_user_data()
    output_file = 'iam_user.json'
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=datetime_handler)
