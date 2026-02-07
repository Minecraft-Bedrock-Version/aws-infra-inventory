from __future__ import annotations
from typing import Any, Dict, List

#제외할 User 목록
EXCLUDED_USERS = {
    "cg-web-sqs-manager-cgid7vg6yu5rd0",
    "cloudgoat_hyeok",
    "hyeok",
    "Interludeal",
    "jbbok",
    "lambda_policy_test",
    "LJH_03",
    "pandyo",
    "yangyu",
    "cg-sqs-user-cgid7vg6yu5rd0"
}

#IAM User와 각 User에 연결된 인라인, 관리형 정책 + 그룹과 그 그룹에 연결된 인라인, 관리형 정책 수집
def collect_iam_user(session) -> Dict[str, Any]:
    #API 호출용 객체 생성
    iam = session.client("iam")
    paginator = iam.get_paginator("list_users")
    
    #User가 저장될 구조 (리스트 안에 딕셔너리가 존재하며, 딕셔너리의 str 키에 어떤 형태로든 값이 들어갈 수 있음)
    users: List[Dict[str, Any]] = []

    #IAM ListUser API를 paginator로 반복 호출
    for page in paginator.paginate(): #User가 많으면 페이지가 넘어가기 때문에 모든 페이지 불러오기
        for user in page["Users"]: #Users 배열 안에 각 User를 불러옴
            username = user["UserName"] #User의 이름을 가져와 연결된 정책과 그룹 조회에 사용

            #제외 대상 User는 제외하여 호출
            if username in EXCLUDED_USERS:
                print(f"[!] Skip user: {username}")
                continue
            
            print(f"[+] Processing User: {username}")
            
            #관리형 정책
            attached_policies: List[Dict[str, Any]] = [] #저장될 구조
            attached_paginator = iam.get_paginator("list_attached_user_policies") #호출 객체 생성
            for attached_page in attached_paginator.paginate(UserName=username):
                for policy in attached_page["AttachedPolicies"]: #User에게 연결된 정책을 하나씩 추가
                    versions = [] #버전 목록 저장용
                    version_list = iam.list_policy_versions(PolicyArn=policy["PolicyArn"])["Versions"] #해당 정책의 버전 목록을 가져옴
                    default_version_id = None 
                    for v in version_list: #버전의 ID와 Default 여부를 표시
                        versions.append({
                            "VersionId": v["VersionId"],
                            "IsDefaultVersion": v["IsDefaultVersion"],
                            "Document": None 
                        })
                        if v["IsDefaultVersion"]: #만약 Default가 true라면
                            default_version_id = v["VersionId"] #해당 버전을 일단 변수에 저장해두고,

                    for v in versions: #각 버전의 정책 세부 내용 가져오기
                        version_detail = iam.get_policy_version(
                            PolicyArn=policy["PolicyArn"],
                            VersionId=v["VersionId"]
                        )
                        v["Document"] = version_detail["PolicyVersion"]["Document"]

                    #버전 목록(각 버전의 id와 default 여부, 정책 내용)을 저장
                    policy["Versions"] = versions
                    policy["DefaultVersionId"] = default_version_id #default 버전을 따로 명시
                    attached_policies.append(policy)

            #인라인 정책
            inline_policies: List[str] = [] #저장될 구조
            inline_paginator = iam.get_paginator("list_user_policies") #호출 객체 생성
            for inline_page in inline_paginator.paginate(UserName=username):
                for policy_name in inline_page["PolicyNames"]: #연결된 인라인 정책의 내용을 불러옴
                    policy_detail = iam.get_user_policy(UserName=username, PolicyName=policy_name)
                    inline_policies.append({
                        "PolicyName": policy_name, #정책 이름
                        "PolicyDocument": policy_detail["PolicyDocument"] #정책 내용 
                    })
                    
            #그룹
            groups: List[Dict[str, Any]] = []
            group_paginator = iam.get_paginator("list_groups_for_user") #호출 객체 생성
            for group_page in group_paginator.paginate(UserName=username): #User에게 연결된 그룹을 하나씩 가져옴
                for group in group_page["Groups"]: #Groups 배열 안에 그룹 들을 하나씩 불러와서
                    group_name = group["GroupName"] #그룹의 정책 조회에 사용될 Group Name을 불러옴

                    #그룹 - 관리형 정책
                    group_attached: List[Dict[str, Any]] = [] #저장될 구조
                    attached_group_paginator = iam.get_paginator("list_attached_group_policies") #호출 객체 생성
                    for g_attached_page in attached_group_paginator.paginate(GroupName=group_name):
                        for policy in g_attached_page["AttachedPolicies"]: #Group에 연결된 정책을 하나씩 추가
                            versions = [] #버전 목록 저장용
                            version_list = iam.list_policy_versions(PolicyArn=policy["PolicyArn"])["Versions"] #해당 정책의 버전 목록을 가져옴
                            default_version_id = None 
                            for v in version_list: #버전의 ID와 Default 여부를 표시
                                versions.append({
                                    "VersionId": v["VersionId"],
                                    "IsDefaultVersion": v["IsDefaultVersion"],
                                    "Document": None 
                                })
                                if v["IsDefaultVersion"]: #만약 Default가 true라면
                                    default_version_id = v["VersionId"] #해당 버전을 일단 변수에 저장해두고,

                            for v in versions: #각 버전의 정책 세부 내용 가져오기
                                version_detail = iam.get_policy_version(
                                    PolicyArn=policy["PolicyArn"],
                                    VersionId=v["VersionId"]
                                )
                                v["Document"] = version_detail["PolicyVersion"]["Document"]

                            #버전 목록(각 버전의 id와 default 여부, 정책 내용)을 저장
                            policy["Versions"] = versions
                            policy["DefaultVersionId"] = default_version_id #default 버전을 따로 명시
                            attached_policies.append(policy)

                    #그룹 - 인라인 정책
                    group_inline: List[str] = [] #저장될 구조
                    inline_group_paginator = iam.get_paginator("list_group_policies") #호출 객체 생성
                    for g_inline_page in inline_group_paginator.paginate(GroupName=group_name):
                        for policy_name in g_inline_page["PolicyNames"]: #연결된 인라인 정책의 내용을 불러옴
                            policy_detail = iam.get_group_policy(GroupName=group_name, PolicyName=policy_name)
                            group_inline.append({
                                "PolicyName": policy_name, #정책 이름
                                "PolicyDocument": policy_detail["PolicyDocument"] #정책 내용 
                            })
                            
                    #그룹에 연결된 정책을 그룹 딕셔너리에 추가
                    group["AttachedPolicies"] = group_attached
                    group["InlinePolicies"] = group_inline
                    groups.append(group) 

            #--- (수정) 추가 수집 ---

            #User 태그 목록 수집
            user_tag = iam.list_user_tags(UserName=username)

            #MFA 기기 상태 수집
            mfa_device = iam.list_mfa_devices(UserName=username)

            #Access Key 목록 수집
            access_key = iam.list_access_keys(UserName=username)
                    
            #수집된 모든 데이터를 User 객체에 통합 저장
            user["Tags"] = user_tag.get("Tags", [])
            user["MFADevices"] = mfa_device.get("MFADevices", [])
            user["AccessKeys"] = access_key.get("AccessKeyMetadata", [])
            user["AttachedPolicies"] = attached_policies
            user["InlinePolicies"] = inline_policies
            user["Groups"] = groups

            users.append(user)

    return {
        "count": len(users), #User 수
        "users": users #User 리스트
    }