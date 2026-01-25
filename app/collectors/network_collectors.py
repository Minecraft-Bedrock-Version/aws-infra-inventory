from __future__ import annotations

import botocore
from typing import Any, Dict, List
from datetime import datetime, timezone

def collect_network(session, region: str):
    ec2 = session.client("ec2", region_name=region)

    # 결과 데이터를 담을 구조
    items = {
        "vpcs": [],
        "subnets": [],
        "igws": [],
        "route_tables": []
    }

    collected_at = datetime.now(timezone.utc).isoformat()

    # VPC 
    api_sources_vpc = ["ec2:DescribeVpcs"]
    vpc_paginator = ec2.get_paginator("describe_vpcs")

    for page in vpc_paginator.paginate():
        for vpc in page.get("Vpcs", []):
            # vpc 딕셔너리에 직접 메타데이터를 주입하여 평탄하게 저장
            vpc.update({
                "region": region,
                "api_sources": api_sources_vpc,
                "collected_at": collected_at
            })
            items["vpcs"].append(vpc)

    # Subnet
    api_sources_subnet = ["ec2:DescribeSubnets"]
    subnet_paginator = ec2.get_paginator("describe_subnets")

    for page in subnet_paginator.paginate():
        for sn in page.get("Subnets", []):
            sn.update({
                "region": region,
                "api_sources": api_sources_subnet,
                "collected_at": collected_at
            })
            items["subnets"].append(sn)

    # Internet Gateway 
    api_sources_igw = ["ec2:DescribeInternetGateways"]
    igw_paginator = ec2.get_paginator("describe_internet_gateways")

    for page in igw_paginator.paginate():
        for igw in page.get("InternetGateways", []):
            igw.update({
                "region": region,
                "api_sources": api_sources_igw,
                "collected_at": collected_at
            })
            items["igws"].append(igw)

    # Route Table
    api_sources_rt = ["ec2:DescribeRouteTables"]
    rt_paginator = ec2.get_paginator("describe_route_tables")

    for page in rt_paginator.paginate():
        for rt in page.get("RouteTables", []):
            rt.update({
                "region": region,
                "api_sources": api_sources_rt,
                "collected_at": collected_at
            })
            items["route_tables"].append(rt)

    return items