from __future__ import annotations
from typing import Any, Dict
from datetime import timezone

def normalize_rds(raw_payload: Dict[str, Any], account_id: str, region: str) -> Dict[str, Any]:
    #Node 생성
    instances = raw_payload.get("instances", [])
    nodes = []
    for instance_value in instances:
        instance_id = instance_value.get("DBInstanceIdentifier")
        endpoint = instance_value.get("Endpoint")
        
        #각 필드를 채우기 위한 값
        node_type = "rds_instance"
        node_id = f"{account_id}:{region}:rds:{instance_id}"
        #resoucre id == instance id
        name = instance_value.get("DBName")
        instance_class = instance_value.get("DBInstanceClass")
        engine = instance_value.get("Engine")
        engine_version = instance_value.get("EngineVersion")
        status = instance_value.get("DBInstanceStatus")
        endpoint_address = endpoint.get("Address")
        endpoint_port = endpoint.get("Port")
        allocated_storage = instance_value.get("AllocatedStorage")
        storage_type = instance_value.get("StorageType")
        storage_encrypted = instance_value.get("StorageEncrypted")
        multi_az = instance_value.get("MultiAZ")
        publicly_accessible = instance_value.get("PubliclyAccessible")
        created_timestamp = instance_value.get("InstanceCreateTime")

        node = {
            "node_type": node_type,
            "node_id": node_id,
            "resource_id": instance_id,
            "name": name,
            "account_id": account_id,
            "region": region,
            "attributes": {
                "instance_class": instance_class,
                "engine": engine,
                "engine_version": engine_version,
                "status": status,
                "endpoint_address": endpoint_address,
                "endpoint_port": endpoint_port,
                "allocated_storage": allocated_storage,
                "storage_type": storage_type,
                "storage_encrypted": storage_encrypted,
                "multi_az": multi_az,
                "publicly_accessible": publicly_accessible,
                "created_timestamp": _iso(created_timestamp)
            }
        }
        nodes.append(node)
    
    return nodes

def _iso(dt_obj: Any) -> str | None: #json 처리를 위한 str 변환 및 시간 표준화
    if dt_obj is None: return None
    try:
        return dt_obj.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception: return str(dt_obj)