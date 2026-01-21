from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime, timezone
import base64
import re

# UserData에서 SQS / RDS 엔드포인트 검출용 정규식
SQS_PATTERN = r"https://sqs\.([a-z0-9-]+)\.amazonaws\.com/[^\s'\"]+"
RDS_PATTERN = r"[^\s'\"/]+\.([a-z0-9-]+)\.rds\.amazonaws\.com"


# 1. EC2 리소스 정규화
def normalize_ec2(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    normalized_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    raw = raw_payload.get("raw", {})
    collected_at = raw_payload.get("collected_at")

    instances = raw.get("describe_instances", [])
    key_pairs = raw.get("describe_key_pairs", [])
    user_data_map = raw.get("describe_instance_attribute_userData", {})

    nodes: List[Dict[str, Any]] = []
    instance_id_to_key_name: Dict[str, str] = {}

    # 1-1. EC2 Instance 노드 생성 및 UserData 분석
    for inst in instances:
        iid = inst.get("InstanceId")
        if not iid: 
            continue

        node_id = f"{account_id}:{region}:ec2:{iid}"
        
        # 이름 추출 (Tag: Name 우선)
        name = next((t.get("Value") for t in inst.get("Tags", []) if t.get("Key") == "Name"), iid)

        # UserData 분석 (SQS/RDS 엔드포인트 탐지)
        sqs_info = {"detected": False, "queue_url": None}
        rds_info = {"detected": False, "db_endpoint": None}
        
        ud_attr = user_data_map.get(iid) or {}
        ud_val = (ud_attr.get("UserData") or {}).get("Value")

        if ud_val:
            try:
                decoded_ud = base64.b64decode(ud_val).decode("utf-8", errors="ignore")
                
                # SQS 패턴 매칭
                s_match = re.search(SQS_PATTERN, decoded_ud)
                if s_match: 
                    sqs_info = {"detected": True, "queue_url": s_match.group(0)}
                
                # RDS 패턴 매칭
                r_match = re.search(RDS_PATTERN, decoded_ud)
                if r_match: 
                    rds_info = {"detected": True, "db_endpoint": r_match.group(0)}
            except Exception: 
                pass

        key_name = inst.get("KeyName")
        if key_name: 
            instance_id_to_key_name[iid] = key_name

        node = {
            "node_type": "ec2_instance",
            "node_id": node_id,
            "resource_id": iid,
            "name": name,
            "account_id": account_id,
            "region": region,

            # 인스턴스 상세 속성 (네트워크, 상태, UserData 분석 결과 등)
            "attributes": {
                "instance_type": inst.get("InstanceType"),
                "state": (inst.get("State") or {}).get("Name"),
                "public": inst.get("PublicIpAddress") is not None,
                "public_ip": inst.get("PublicIpAddress"),
                "private_ip": inst.get("PrivateIpAddress"),
                "launch_time": _iso(inst.get("LaunchTime")),
                "vpc_id": inst.get("VpcId"),
                "subnet_id": inst.get("SubnetId"),
                "key_name": key_name,
                "iam_instance_profile": (inst.get("IamInstanceProfile") or {}).get("Arn"),
                "security_groups": [
                    {"group_id": sg.get("GroupId"), "group_name": sg.get("GroupName")}
                    for sg in inst.get("SecurityGroups", []) if sg.get("GroupId")
                ],
                "sqs_info": sqs_info,
                "rds_info": rds_info
            },

            # 관계 정보 (VPC, 키 페어, 보안 그룹 매핑)
            "relationships": {
                "key_name": key_name,
                "vpc_id": inst.get("VpcId"),
                "security_groups": [sg.get("GroupId") for sg in inst.get("SecurityGroups", []) if sg.get("GroupId")]
            },

            # 데이터 원천 및 수집 정보
            "raw_refs": {
                "source": ["describe_instances", "describe_instance_attribute(userData)"],
                "collected_at": collected_at
            }
        }
        nodes.append(node)

    # 1-2. Key Pair 노드 생성
    for kp in key_pairs:
        k_name = kp.get("KeyName")
        k_id = kp.get("KeyPairId") or k_name
        if not k_id: 
            continue

        node = {
            "node_type": "key_pair",
            "node_id": f"{account_id}:{region}:key_pair:{k_id}",
            "resource_id": k_id,
            "name": k_name,

            # 키 페어 상세 정보
            "attributes": {
                "key_type": kp.get("KeyType"),
                "key_fingerprint": kp.get("KeyFingerprint"),
                "create_time": _iso(kp.get("CreateTime")),
                "tags": {t.get("Key"): t.get("Value") for t in kp.get("Tags", []) if t.get("Key")}
            },

            # 관계 정보 (해당 키 페어를 사용하는 인스턴스 역추적)
            "relationships": {
                "used_by_instances": [iid for iid, kn in instance_id_to_key_name.items() if kn == k_name]
            },

            # 데이터 원천 정보
            "raw_refs": {
                "source": ["describe_key_pairs"],
                "collected_at": collected_at
            }
        }
        nodes.append(node)

    return {
        "schema_version": "1.0",
        "collected_at": normalized_at,
        "account_id": account_id,
        "nodes": nodes
    }


# 2. 타임존을 포함한 ISO 포맷 변환
def _iso(dt_obj: Any) -> str | None:
    if dt_obj is None: 
        return None
    try:
        return dt_obj.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception: 
        return str(dt_obj)
