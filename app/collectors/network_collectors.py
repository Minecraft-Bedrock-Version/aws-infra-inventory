from __future__ import annotations
from typing import Any, Dict, List

#VPC, Subnet, IGW, Route Table 각각 수집
def collect_network(session, region: str):
    #API 호출용 객체 생성
    ec2 = session.client("ec2", region_name=region)
    vpcs = []
    subnets = []
    igws = []
    route_tables = []
    security_groups = [] #(수정) SG 추가

    #VPC
    paginator_vpc = ec2.get_paginator("describe_vpcs")
    for page in paginator_vpc.paginate(): #모든 페이지 불러오기
        for vpc in page.get("Vpcs",[]):
            vpc_id = vpc["VpcId"]
            print(f"[+] Processing VPC: {vpc_id}")
            vpcs.append(vpc)

    #Subnet
    paginator_vpc = ec2.get_paginator("describe_subnets")
    for page in paginator_vpc.paginate(): #모든 페이지 불러오기
        for subnet in page.get("Subnets", []):
            subnet_id = subnet["SubnetId"]
            print(f"[+] Processing Subnet: {subnet_id}")
            subnets.append(subnet)

    #Internet Gateway 
    paginator_igw = ec2.get_paginator("describe_internet_gateways")
    for page in paginator_igw.paginate(): #모든 페이지 불러오기
        for igw in page.get("InternetGateways", []):
            igw_id = igw["InternetGatewayId"]
            print(f"[+] Processing Internet Gateway: {igw_id}")
            igws.append(igw)

    #Route Table
    paginator_route = ec2.get_paginator("describe_route_tables")
    for page in paginator_route.paginate(): #모든 페이지 불러오기
        for route in page.get("RouteTables", []):
            route_id = route["RouteTableId"]
            print(f"[+] Processing Route Table: {route_id}")
            route_tables.append(route)  

    #(수정)Security Group
    paginator_sg = ec2.get_paginator("describe_security_groups")
    for page in paginator_sg.paginate():
        for sg in page.get("SecurityGroups", []):
            sg_id = sg["GroupId"]
            print(f"[+] Processing Security Group: {sg_id}")
            security_groups.append(sg) 
            
    items = {
        "vpc": {
            "region": region,
            "count": len(vpcs),
            "Vpcs": vpcs
        },
        "subnet": {
            "region": region,
            "count": len(subnets),
            "Subnets": subnets
        },
        "igw": {
            "region": region,
            "count": len(igws),
            "InternetGateways": igws
        },
        "route_table": {
            "region": region,
            "count": len(route_tables),
            "RouteTables": route_tables
        },
        "security_group": {
            "region": region,
            "count": len(security_groups),
            "SecurityGroups": security_groups
        }
    }

    return items
