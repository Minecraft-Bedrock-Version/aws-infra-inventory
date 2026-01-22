from __future__ import annotations

import botocore
from typing import Any, Dict, List
from datetime import datetime, timezone

def collect_rds(session, region: str):
    client = session.client("rds", region_name="us-east-1")
    collected_at = datetime.now(timezone.utc).isoformat()

    # 결과 데이터를 담을 구조
    items = {
        "db_instances": [],
        "db_clusters": [],
        "db_subnet_groups": [],
        "tags_by_arn": {},
        "api_sources": [],
        "region": region,
        "collected_at": collected_at
    }

		# 태그 수집
    def _collect_tags(arn: str):
        try:
            resp = client.list_tags_for_resource(ResourceName=arn)
            items["tags_by_arn"][arn] = resp.get("TagList", [])
        except Exception:
            items["tags_by_arn"][arn] = []

    # 1. DB Instances
    try:
        api_vpc = ["rds:DescribeDBInstances"]
        paginator = client.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                items["db_instances"].append(db)

                if db.get("DBInstanceArn"):
                    _collect_tags(db["DBInstanceArn"])
    except Exception as e:
        print(f"[-] RDS Instances 수집 실패 ({region}): {e}")

    # 2. DB Clusters 
    try:
        paginator = client.get_paginator("describe_db_clusters")
        for page in paginator.paginate():
            for cluster in page.get("DBClusters", []):
                items["db_clusters"].append(cluster)
                if cluster.get("DBClusterArn"):
                    _collect_tags(cluster["DBClusterArn"])
    except Exception as e:
        print(f"[-] RDS Clusters 수집 실패 ({region}): {e}")

    # 3. DB Subnet Groups 
    try:
        paginator = client.get_paginator("describe_db_subnet_groups")
        for page in paginator.paginate():
            for sg in page.get("DBSubnetGroups", []):
                items["db_subnet_groups"].append(sg)
                if sg.get("DBSubnetGroupArn"):
                    _collect_tags(sg["DBSubnetGroupArn"])
    except Exception as e:
        print(f"[-] RDS Subnet Groups 수집 실패 ({region}): {e}")

    return items
