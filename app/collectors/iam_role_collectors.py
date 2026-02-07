from __future__ import annotations
from typing import Any, Dict, List

#제외할 Role 목록
EXCLUDED_ROLES = {
    "AWSServiceRoleForAmazonEventBridgeApiDestinations",
    "AWSServiceRoleForRDS",
    "AWSServiceRoleForResourceExplorer",
    "AWSServiceRoleForSupport",
    "AWSServiceRoleForTrustedAdvisor",
    "mbvCodebuildRole",
    "mbvEC2Role",
    "mbvLambdaGraphRole",
    "mbvLambdaRole",
    "mbvLambdaSlackRole",
    "AWSServiceRoleForECS",
    "AWSServiceRoleForAPIGateway",
    "AWSServiceRoleForAmazonElasticFileSystem"
}

#IAM Role과 각 Role에 연결된 인라인, 관리형 정책 + 어떤 주체가 해당 Role을 Assume 할 수 있는지
def collect_iam_role(session) -> Dict[str, Any]:
    #API 호출용 객체 생성
    iam = session.client("iam")
    paginator = iam.get_paginator("list_roles")
    
    #Role이 저장될 구조 (리스트 안에 딕셔너리가 존재하며, 딕셔너리의 str 키에 어떤 형태로든 값이 들어갈 수 있음)
    roles: List[Dict[str, Any]] = []

    #IAM ListRole API를 paginator로 반복 호출
    for page in paginator.paginate(): #Role이 많으면 페이지가 넘어가기 때문에 모든 페이지 불러오기
        for role in page["Roles"]: #Roles 배열 안에 각 Role을 불러옴
            role_name = role["RoleName"] #Role의 이름을 가져와 연결된 정책 조회에 사용
            
            #제외 대상 Role은 제외하여 호출
            if role_name in EXCLUDED_ROLES:
                print(f"[!] Skip role: {role_name}")
                continue
            
            print(f"[+] Processing role: {role_name}")

            #관리형 정책
            attached_policies: List[Dict[str, Any]] = [] #저장될 구조
            attached_paginator = iam.get_paginator("list_attached_role_policies") #호출 객체 생성
            for attached_page in attached_paginator.paginate(RoleName=role_name):
                for policy in attached_page["AttachedPolicies"]: #Role에 연결된 정책을 하나씩 추가
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

            inline_policies: List[str] = [] #저장될 구조
            inline_paginator = iam.get_paginator("list_role_policies") #호출 객체 생성
            for inline_page in inline_paginator.paginate(RoleName=role_name):
                for policy_name in inline_page["PolicyNames"]: #연결된 인라인 정책의 내용을 불러옴
                    policy_detail = iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                    inline_policies.append({
                        "PolicyName": policy_name, #정책 이름
                        "PolicyDocument": policy_detail["PolicyDocument"] #정책 내용 
                    })

            #--- (수정) 추가 수집 ---
            
            # Role 태그 목록 수집
            tag = iam.list_role_tags(RoleName=role_name)
                    
            #어떤 주체가 Assume할 수 있는지 GET으로 확인
            trust_policy = None
            role_detail = iam.get_role(RoleName=role_name) #Role의 이름을 이용해 Get Role
            if "AssumeRolePolicyDocument" in role_detail["Role"]: #AssumeRolePolicyDocument가 존재하면
                trust_policy = role_detail["Role"]["AssumeRolePolicyDocument"] #trust_policy에 추가

            #최종적으로 Role 하나의 관리형, 인라인 정책과 Assume 대상, 태그 정보 저장
            role["AttachedPolicies"] = attached_policies
            role["InlinePolicies"] = inline_policies
            role["AssumeRolePolicyDocument"] = trust_policy
            role["Tags"] = tag.get("Tags", [])

            roles.append(role)

    return {
        "count": len(roles), #역할 수
        "roles": roles #역할 리스트
    }