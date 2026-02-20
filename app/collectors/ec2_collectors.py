from __future__ import annotations
from typing import Any, Dict, List
import base64
import re

#EC2 인스턴스 (user data 포함)
def collect_ec2(session, region: str) -> Dict[str, Any]:
    #API 호출용 객체 생성
    ec2 = session.client("ec2", region_name=region)
    iam = session.client("iam", region_name=region) #instance profile에 연결된 iam role 정보 수집용 객체
    paginator = ec2.get_paginator("describe_instances")
    
    #인스턴스가 저장될 구조 (리스트 안에 딕셔너리가 존재하며, 딕셔너리의 str 키에 어떤 형태로든 값이 들어갈 수 있음)
    instances: List[Dict[str, Any]] = []

    #EC2 DescribeInstances API를 paginator로 반복 호출
    for page in paginator.paginate(): #인스턴스가 많으면 페이지가 넘어가기 때문에 모든 페이지 불러오기
        for reservation in page["Reservations"]: #내부적으로 묶여서 반환되는 Reservations 단위로 다시 불러와서
            for instance in reservation["Instances"]: #Instances 배열 안에 인스턴스들을 가져옴
                
                instance_id = instance["InstanceId"] #각 인스턴스의 ID를 가져와서
                
                print(f"[+] Processing EC2 Instance: {instance_id}")
                
                #해당 인스턴스 ID의 인스턴스에서 속성값을 추가로 가져오도록 attribute 호출
                base64_user_data = ec2.describe_instance_attribute(InstanceId=instance_id, Attribute="userData")
                #없으면 None로
                user_data = None
                ecs_cluster_name = None #(수정) ecs 클러스터 이름 필드 추가

                #UserData라는 키가 존재하고 해당 키의 Value 값이 존재하면
                if "UserData" in base64_user_data and "Value" in base64_user_data["UserData"]:
                    #Value 값을 base64 디코딩하여 userdata 변수에 저장
                    user_data = base64.b64decode(base64_user_data["UserData"]["Value"]).decode("utf-8")

                    #(수정) ecs 클러스터 이름 추출
                    match = re.search(r"ECS_CLUSTER=([^\s]+)", user_data)
                    if match:
                        ecs_cluster_name = match.group(1).strip()

                instance["UserData"] = user_data #해당 instance 리스트에 UserData 값을 실제 값으로 추가
                instance["EcsClusterName"] = ecs_cluster_name # (수정) 클러스터 이름 필드 추가

                #엣지 생성 시, instanceprofile과 iam role 의 연결 관계를 참조하기 위함 
                instance["BoundRoleNames"] = []
                
                #IamInstanceProfile이 존재한다면
                if "IamInstanceProfile" in instance:
                    # ARN에서 프로필 이름만 추출
                    profile_arn = instance["IamInstanceProfile"]["Arn"]
                    profile_name = profile_arn.split('/')[-1]
                    
                    try:
                        #IAM API를 통해 실제 연결된 Role 정보를 가져옴
                        profile_response = iam.get_instance_profile(InstanceProfileName=profile_name)
                        roles = profile_response.get("InstanceProfile", {}).get("Roles", []) #응답 데이터 중 'Roles' 리스트를 가져옴
                        
                        #Role Name 리스트 저장
                        instance["BoundRoleNames"] = [r["RoleName"] for r in roles]
                    except Exception as e:
                        print(f"[-] Failed to fetch IAM Role for profile {profile_name}: {e}")


                instances.append(instance) #위에 정의해둔 구조에 인스턴스 딕셔너리를 하나씩 넣음

    return {
        "region": region, #리전
        "count": len(instances), #인스턴스 개수
        "instances": instances #인스턴스 리스트
    }
