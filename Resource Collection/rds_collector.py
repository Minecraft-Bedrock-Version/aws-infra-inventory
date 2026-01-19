# collectors/rds_collector.py
from __future__ import annotations

import botocore
from typing import Any, Dict, List


def collect_rds(session, region: str) -> Dict[str, Any]:
    client = session.client("rds", region_name=region)

    instances: List[Dict[str, Any]] = []
    clusters: List[Dict[str, Any]] = []

    # DB Instances
    try:
        p = client.get_paginator("describe_db_instances")
        for page in p.paginate():
            for db in page.get("DBInstances", []):
                item = {
                    "DBInstanceIdentifier": db.get("DBInstanceIdentifier"),
                    "DBInstanceArn": db.get("DBInstanceArn"),
                    "Engine": db.get("Engine"),
                    "EngineVersion": db.get("EngineVersion"),
                    "DBInstanceClass": db.get("DBInstanceClass"),
                    "DBInstanceStatus": db.get("DBInstanceStatus"),
                    "Endpoint": db.get("Endpoint", {}),
                    "PubliclyAccessible": db.get("PubliclyAccessible"),
                    "StorageEncrypted": db.get("StorageEncrypted"),
                    "KmsKeyId": db.get("KmsKeyId"),
                    "VpcSecurityGroups": db.get("VpcSecurityGroups", []),
                    "DBSubnetGroup": db.get("DBSubnetGroup", {}),
                    "MultiAZ": db.get("MultiAZ"),
                    "IAMDatabaseAuthenticationEnabled": db.get("IAMDatabaseAuthenticationEnabled"),
                    "AssociatedRoles": db.get("AssociatedRoles", []),
                    "Tags": {},
                    "Raw": db,  # 필요하면 제거 가능 (원문 보존)
                }

                arn = db.get("DBInstanceArn")
                if arn:
                    try:
                        tags = client.list_tags_for_resource(ResourceName=arn)
                        item["Tags"] = tags.get("TagList", [])
                    except botocore.exceptions.ClientError as e:
                        item["list_tags_error"] = _err(e)

                instances.append(item)
    except botocore.exceptions.ClientError as e:
        return {"service": "rds", "region": region, "error": _err(e)}

    # DB Clusters (Aurora 등)
    try:
        p = client.get_paginator("describe_db_clusters")
        for page in p.paginate():
            for cl in page.get("DBClusters", []):
                item = {
                    "DBClusterIdentifier": cl.get("DBClusterIdentifier"),
                    "DBClusterArn": cl.get("DBClusterArn"),
                    "Engine": cl.get("Engine"),
                    "EngineVersion": cl.get("EngineVersion"),
                    "Status": cl.get("Status"),
                    "Endpoint": cl.get("Endpoint"),
                    "ReaderEndpoint": cl.get("ReaderEndpoint"),
                    "StorageEncrypted": cl.get("StorageEncrypted"),
                    "KmsKeyId": cl.get("KmsKeyId"),
                    "VpcSecurityGroups": cl.get("VpcSecurityGroups", []),
                    "DBSubnetGroup": cl.get("DBSubnetGroup"),
                    "IAMDatabaseAuthenticationEnabled": cl.get("IAMDatabaseAuthenticationEnabled"),
                    "AssociatedRoles": cl.get("AssociatedRoles", []),
                    "Tags": {},
                    "Raw": cl,
                }

                arn = cl.get("DBClusterArn")
                if arn:
                    try:
                        tags = client.list_tags_for_resource(ResourceName=arn)
                        item["Tags"] = tags.get("TagList", [])
                    except botocore.exceptions.ClientError as e:
                        item["list_tags_error"] = _err(e)

                clusters.append(item)
    except botocore.exceptions.ClientError as e:
        # 클러스터 권한 없으면 인스턴스는 살리고 클러스터만 에러 기록
        clusters.append({"error": _err(e)})

    return {"service": "rds", "region": region, "db_instances": instances, "db_clusters": clusters}


def _err(e: Exception) -> Dict[str, Any]:
    if hasattr(e, "response"):
        r = getattr(e, "response", {}) or {}
        return {"Error": r.get("Error", {}), "ResponseMetadata": r.get("ResponseMetadata", {})}
    return {"Error": {"Message": str(e)}}


if __name__ == "__main__":
    import argparse, boto3, json

    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=None)
    ap.add_argument("--region", default="ap-northeast-2")
    args = ap.parse_args()

    sess = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    data = collect_rds(sess, args.region)
    print(json.dumps(data, ensure_ascii=False, indent=2))