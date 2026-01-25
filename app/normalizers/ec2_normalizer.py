from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime, timezone
import base64
import re

# UserData에서 SQS / RDS 엔드포인트 검출용 정규식
SQS_PATTERN = r"https://sqs\.([a-z0-9-]+)\.amazonaws\.com/[^\s'\"]+"
RDS_PATTERN = r"[^\s'\"/]+\.([a-z0-9-]+)\.rds\.amazonaws\.com"

def normalize_ec2(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    """
    EC2 및 KeyPair 원본 데이터를 그래프 분석을 위한 표준 포맷으로 정규화합니다.
    """
    normalized_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    raw = raw_payload.get("raw", {})
    collected_at = raw_payload.get("collected_at")

    instances = raw.get("describe_instances", [])
    key_pairs = raw.get("describe_key_pairs", [])
    user_data_map = raw.get("describe_instance_attribute_userData", {})
    internet_gateways = raw.get("describe_internet_gateways", [])

    nodes: List[Dict[str, Any]] = []
    instance_id_to_key_name: Dict[str, str] = {}
    
    # VPC별 IGW 매핑
    vpc_to_igw: Dict[str, str] = {}
    for igw in internet_gateways:
        igw_id = igw.get("InternetGatewayId")
        for attachment in igw.get("Attachments", []):
            vpc_id = attachment.get("VpcId")
            if vpc_id:
                vpc_to_igw[vpc_id] = igw_id

    # 1. EC2 Instance Nodes 처리
    for inst in instances:
        iid = inst.get("InstanceId")
        if not iid: continue

        node_id = f"{account_id}:{region}:ec2:{iid}"
        
        # 이름 추출 (Tag: Name)
        name = next((t.get("Value") for t in inst.get("Tags", []) if t.get("Key") == "Name"), iid)

        # UserData 분석 (SQS/RDS 엔드포인트 탐지)
        sqs_info = {"detected": False, "queue_url": None, "node_id": None}
        rds_info = {"detected": False, "db_endpoint": None, "node_id": None}
        
        ud_attr = user_data_map.get(iid) or {}
        ud_val = (ud_attr.get("UserData") or {}).get("Value")
        if ud_val:
            try:
                decoded_ud = base64.b64decode(ud_val).decode("utf-8", errors="ignore")
                
                s_match = re.search(SQS_PATTERN, decoded_ud)
                if s_match:
                    queue_url = s_match.group(0)
                    # SQS URL에서 queue name 추출
                    # 예: https://sqs.us-east-1.amazonaws.com/288528695623/cash_charging_queue -> cash_charging_queue
                    queue_name = queue_url.split("/")[-1]
                    sqs_node_id = f"{account_id}:{region}:sqs:{queue_name}"
                    sqs_info = {
                        "detected": True,
                        "queue_url": queue_url,
                        "node_id": sqs_node_id
                    }
                
                r_match = re.search(RDS_PATTERN, decoded_ud)
                if r_match:
                    db_endpoint = r_match.group(0)
                    # RDS endpoint에서 db_identifier 추출 (첫 번째 . 앞부분)
                    # 예: mydb.c9akciq32.us-east-1.rds.amazonaws.com -> mydb
                    db_identifier = db_endpoint.split(".")[0]
                    rds_node_id = f"{account_id}:{region}:rds_instance:{db_identifier}"
                    rds_info = {
                        "detected": True,
                        "db_endpoint": db_endpoint,
                        "node_id": rds_node_id
                    }
            except Exception: pass

        key_name = inst.get("KeyName")
        if key_name: instance_id_to_key_name[iid] = key_name

        # IGW 정보 구성 (public EC2의 경우)
        igw_info = {"detected": False, "igw_id": None, "node_id": None}
        vpc_id = inst.get("VpcId")
        public_ip = inst.get("PublicIpAddress")
        if public_ip and vpc_id and vpc_id in vpc_to_igw:
            igw_id = vpc_to_igw[vpc_id]
            igw_node_id = f"{account_id}:{region}:igw:{igw_id}"
            igw_info = {
                "detected": True,
                "igw_id": igw_id,
                "node_id": igw_node_id
            }

        node = {
            "node_type": "ec2_instance",
            "node_id": node_id,
            "resource_id": iid,
            "name": name,
            "account_id": account_id,
            "region": region,
            "attributes": {
                "instance_type": inst.get("InstanceType"),
                "state": (inst.get("State") or {}).get("Name"),
                "public": public_ip is not None,
                "public_ip": public_ip,
                "private_ip": inst.get("PrivateIpAddress"),
                "launch_time": _iso(inst.get("LaunchTime")),
                "vpc_id": vpc_id,
                "subnet_id": inst.get("SubnetId"),
                "key_name": key_name,
                "iam_instance_profile": (inst.get("IamInstanceProfile") or {}).get("Arn"),
                "security_groups": [
                    {"group_id": sg.get("GroupId"), "group_name": sg.get("GroupName")}
                    for sg in inst.get("SecurityGroups", []) if sg.get("GroupId")
                ],
                "sqs_info": sqs_info,
                "rds_info": rds_info,
                "igw_info": igw_info
            },
            "relationships": {
                "key_name": key_name,
                "vpc_id": vpc_id,
                "security_groups": [sg.get("GroupId") for sg in inst.get("SecurityGroups", []) if sg.get("GroupId")]
            },
            "raw_refs": {
                "source": ["describe_instances", "describe_instance_attribute(userData)"],
                "collected_at": collected_at
            }
        }
        nodes.append(node)

    # 2. Key Pair Nodes 처리
    for kp in key_pairs:
        k_name = kp.get("KeyName")
        k_id = kp.get("KeyPairId") or k_name
        if not k_id: continue

        node = {
            "node_type": "key_pair",
            "node_id": f"{account_id}:{region}:key_pair:{k_id}",
            "resource_id": k_id,
            "name": k_name,
            "attributes": {
                "key_type": kp.get("KeyType"),
                "key_fingerprint": kp.get("KeyFingerprint"),
                "create_time": _iso(kp.get("CreateTime")),
                "tags": {t.get("Key"): t.get("Value") for t in kp.get("Tags", []) if t.get("Key")}
            },
            "relationships": {
                "used_by_instances": [iid for iid, kn in instance_id_to_key_name.items() if kn == k_name]
            },
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

def _iso(dt_obj: Any) -> str | None:
    if dt_obj is None: return None
    try:
        return dt_obj.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception: return str(dt_obj)