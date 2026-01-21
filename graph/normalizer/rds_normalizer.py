from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime, timezone

# 1. RDS 리소스 데이터 정규화
def normalize_rds(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    normalized_at = datetime.now(timezone.utc).isoformat()
   
    instances = raw_payload.get("db_instances", [])
    subnet_groups = raw_payload.get("db_subnet_groups", [])
    collected_at = raw_payload.get("collected_at")

    nodes: List[Dict[str, Any]] = []

    # 1-1. RDS DB 인스턴스 노드 생성
    for db in instances:
        res_id = db.get("DBInstanceIdentifier")
        if not res_id:
            continue

        node_id = f"{account_id}:{region}:rds:{res_id}"
        endpoint = db.get("Endpoint") or {}
        subnet_group_info = db.get("DBSubnetGroup") or {}

        node = {
            "node_type": "rds_instance",
            "node_id": node_id,
            "resource_id": res_id,
            "name": res_id,
            "account_id": account_id,
            "region": region,
            
            # 인스턴스 상세 속성
            "attributes": {
                "instance_class": db.get("DBInstanceClass"),
                "engine": db.get("Engine"),
                "engine_version": db.get("EngineVersion"),
                "status": db.get("DBInstanceStatus"),
                "db_name": db.get("DBName"),
                "endpoint_address": endpoint.get("Address"),
                "endpoint_port": endpoint.get("Port"),
                "allocated_storage": db.get("AllocatedStorage"),
                "storage_type": db.get("StorageType"),
                "storage_encrypted": db.get("StorageEncrypted"),
                "multi_az": db.get("MultiAZ"),
                "publicly_accessible": db.get("PubliclyAccessible"),
                "created_timestamp": _iso(db.get("InstanceCreateTime")),
            },
            
            # 관계 정보 
            "relationships": {
                "db_instance_arn": db.get("DBInstanceArn"),
                "vpc_id": subnet_group_info.get("VpcId"),
                "subnet_group_name": subnet_group_info.get("DBSubnetGroupName"),
                "security_groups": [
                    sg.get("VpcSecurityGroupId")
                    for sg in db.get("VpcSecurityGroups", [])
                    if sg.get("VpcSecurityGroupId")
                ],
                "kms_key_id": db.get("KmsKeyId"),
            },
            
            # 데이터 원천 정보
            "raw_refs": {
                "source": ["describe_db_instances"],
                "collected_at": collected_at,
            },
        }
        nodes.append(node)

    # 1-2. DB 서브넷 그룹 노드 생성
    for sg in subnet_groups:
        res_id = sg.get("DBSubnetGroupName")
        if not res_id:
            continue

        node_id = f"{account_id}:{region}:rds_subnet_group:{res_id}"

        node = {
            "node_type": "rds_subnet_group",
            "node_id": node_id,
            "resource_id": res_id,
            "name": res_id,
            "account_id": account_id,
            "region": region,
            
            # 서브넷 그룹 상세 정보
            "attributes": {
                "status": sg.get("SubnetGroupStatus"),
                "subnets": [
                    s.get("SubnetIdentifier")
                    for s in sg.get("Subnets", [])
                    if s.get("SubnetIdentifier")
                ],
            },
            
            # 관계 정보 (ARN, VPC)
            "relationships": {
                "subnet_group_arn": sg.get("DBSubnetGroupArn"),
                "vpc_id": sg.get("VpcId"),
            },
            
            # 데이터 원천 정보
            "raw_refs": {
                "source": ["describe_db_subnet_groups"],
                "collected_at": collected_at,
            },
        }
        nodes.append(node)

    # 최종 결과 반환
    return {
        "schema_version": "1.0",
        "collected_at": normalized_at,
        "account_id": account_id,
        "nodes": nodes,
    }


# 2. 타임존을 포함한 ISO 포맷 변환
def _iso(dt_obj: Any) -> Any:
    if dt_obj is None:
        return None
    try:
        return dt_obj.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return str(dt_obj)
