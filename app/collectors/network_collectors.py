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
            
    items = {
        "vpc": {
            "region": region, #리전
            "count": len(vpcs), #vpc 개수
            "Vpcs": vpcs #vpc 리스트
        },
        "subnet": {
            "region": region, #리전
            "count": len(subnets), #Subnets 개수
            "Subnets": subnets #Subnets 리스트
        },
        "igw": {
            "region": region, #리전
            "count": len(igws), #InternetGateways 개수
            "InternetGateways": igws #InternetGateways 리스트
        },
        "route_table": {
            "region": region, #리전
            "count": len(route_tables), #RouteTable 개수
            "RouteTables": route_tables #RouteTable 리스트
        }
    }

    return items