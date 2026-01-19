import boto3
import json
from botocore.exceptions import ClientError

def get_integrated_role_data():
    iam = boto3.client('iam')
    integrated_roles = []

    # 1. 모든 IAM Role 수집
    role_paginator = iam.get_paginator('list_roles')
    for role_page in role_paginator.paginate():
        for role in role_page['Roles']:
            role_name = role['RoleName']
            # 처리 중인 Role 표시 (필요 없다면 삭제 가능)
            print(f"Processing Role: {role_name}")

            # 모든 연결된 관리형 정책(Attached Policies) 수집
            attached_details = []
            attached_paginator = iam.get_paginator('list_attached_role_policies')
            for attached_page in attached_paginator.paginate(RoleName=role_name):
                for p in attached_page['AttachedPolicies']:
                    # 정책의 상세 내용(Document)을 가져오기 위해 기본 버전 확인
                    policy_info = iam.get_policy(PolicyArn=p['PolicyArn'])
                    version_id = policy_info['Policy']['DefaultVersionId']
                    policy_ver = iam.get_policy_version(
                        PolicyArn=p['PolicyArn'], 
                        VersionId=version_id
                    )
                    
                    attached_details.append({
                        "PolicyName": p['PolicyName'],
                        "PolicyArn": p['PolicyArn'],
                        "Statement": policy_ver['PolicyVersion']['Document'].get('Statement')
                    })

            # 모든 인라인 정책(Inline Policies) 수집
            inline_details = []
            inline_paginator = iam.get_paginator('list_role_policies')
            for inline_page in inline_paginator.paginate(RoleName=role_name):
                for p_name in inline_page['PolicyNames']:
                    inline_p = iam.get_role_policy(RoleName=role_name, PolicyName=p_name)
                    inline_details.append({
                        "PolicyName": p_name,
                        "Statement": inline_p['PolicyDocument'].get('Statement')
                    })

            # 데이터 통합
            integrated_roles.append({
                "node_type": "iam_role",
                "name": role_name,
                "resource_id": role['RoleId'],
                "attributes": {
                    "arn": role['Arn'],
                    # 신뢰 관계 (이 역할을 누가 맡을 수 있는가?)
                    "assume_role_policy": role['AssumeRolePolicyDocument'],
                    "inline_policies": inline_details,
                    "attached_policies": attached_details,
                    "create_date": str(role['CreateDate']),
                    "path": role['Path']
                }
            })
            
    return integrated_roles

if __name__ == "__main__":
    try:
        data = get_integrated_role_data()
        output_file = 'iam_role.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        print(f"\n성공: 총 {len(data)}개의 Role 데이터를 {output_file}에 저장했습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
