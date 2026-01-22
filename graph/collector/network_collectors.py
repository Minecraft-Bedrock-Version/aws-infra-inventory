from __future__ import annotations

import botocore
from typing import Any, Dict, List
from datetime import datetime, timezone

def collect_ec2_network(region=None):

    session = boto3.Session(region_name=region)
    ec2 = session.client("ec2", region_name="us-east-1")

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
            items["vpcs"].append({
                "vpc": vpc,
                "region": region,  
                "api_sources": api_sources_vpc,
                "collected_at": collected_at
            })

    # Subnet
    api_sources_subnet = ["ec2:DescribeSubnets"]
    subnet_paginator = ec2.get_paginator("describe_subnets")

    for page in subnet_paginator.paginate():
        for sn in page.get("Subnets", []):
            items["subnets"].append({
                "subnet": sn,
                "region": region,  
                "api_sources": api_sources_subnet,
                "collected_at": collected_at
            })

    # Internet Gateway 
    api_sources_igw = ["ec2:DescribeInternetGateways"]
    igw_paginator = ec2.get_paginator("describe_internet_gateways")

    for page in igw_paginator.paginate():
        for igw in page.get("InternetGateways", []):
            items["igws"].append({
                "igw": igw,
                "region": region, 
                "api_sources": api_sources_igw,
                "collected_at": collected_at
            })

    # Route Table
    api_sources_rt = ["ec2:DescribeRouteTables"]
    rt_paginator = ec2.get_paginator("describe_route_tables")

    for page in rt_paginator.paginate():
        for rt in page.get("RouteTables", []):
            items["route_tables"].append({
                "route_table": rt,
                "region": region,  
                "api_sources": api_sources_rt,
                "collected_at": collected_at
            })

    return items
