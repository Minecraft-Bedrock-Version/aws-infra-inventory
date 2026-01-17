#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError


def json_default(o: Any):
    try:
        return str(o)
    except Exception:
        return repr(o)


def utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _session(region: Optional[str] = None) -> boto3.Session:
    # Use explicit region if provided, otherwise rely on env/config.
    if region:
        return boto3.Session(region_name=region)
    return boto3.Session()


def _tag_value(tags: Optional[List[Dict[str, str]]], key: str) -> Optional[str]:
    if not tags:
        return None
    for t in tags:
        if t.get("Key") == key:
            return t.get("Value")
    return None


def get_vpcs(ec2) -> List[Dict[str, Any]]:
    return ec2.describe_vpcs().get("Vpcs", [])


def get_igws(ec2) -> List[Dict[str, Any]]:
    return ec2.describe_internet_gateways().get("InternetGateways", [])


def get_subnets(ec2) -> List[Dict[str, Any]]:
    return ec2.describe_subnets().get("Subnets", [])


def get_route_tables(ec2) -> List[Dict[str, Any]]:
    return ec2.describe_route_tables().get("RouteTables", [])


def is_public_route_table(route_table: Dict[str, Any]) -> bool:
    # Public if it has a default route (0.0.0.0/0) to an Internet Gateway.
    for route in route_table.get("Routes", []) or []:
        if route.get("DestinationCidrBlock") == "0.0.0.0/0":
            gw = route.get("GatewayId", "") or ""
            if gw.startswith("igw-"):
                return True
    return False


def map_subnet_visibility(route_tables: List[Dict[str, Any]]) -> Dict[str, str]:
    # subnet_id -> "public" | "private"
    subnet_visibility: Dict[str, str] = {}

    for rt in route_tables:
        visibility = "public" if is_public_route_table(rt) else "private"
        for assoc in rt.get("Associations", []) or []:
            subnet_id = assoc.get("SubnetId")
            # Main association has no SubnetId
            if subnet_id:
                subnet_visibility[subnet_id] = visibility

    return subnet_visibility


def collect_vpc_inventory(region: Optional[str] = None) -> Dict[str, Any]:
    session = _session(region)
    ec2 = session.client("ec2")

    vpcs = get_vpcs(ec2)
    igws = get_igws(ec2)
    subnets = get_subnets(ec2)
    route_tables = get_route_tables(ec2)

    subnet_visibility = map_subnet_visibility(route_tables)

    inventory: List[Dict[str, Any]] = []

    for vpc in vpcs:
        vpc_id = vpc["VpcId"]

        vpc_igws = []
        for igw in igws:
            for att in igw.get("Attachments", []) or []:
                if att.get("VpcId") == vpc_id:
                    vpc_igws.append(igw.get("InternetGatewayId"))

        vpc_subnets = []
        for sn in subnets:
            if sn.get("VpcId") != vpc_id:
                continue
            sn_id = sn.get("SubnetId")
            vpc_subnets.append(
                {
                    "subnet_id": sn_id,
                    "name": _tag_value(sn.get("Tags"), "Name"),
                    "cidr": sn.get("CidrBlock"),
                    "az": sn.get("AvailabilityZone"),
                    "map_public_ip_on_launch": sn.get("MapPublicIpOnLaunch"),
                    "visibility": subnet_visibility.get(sn_id, "unknown"),
                }
            )

        vpc_rts = []
        for rt in route_tables:
            if rt.get("VpcId") != vpc_id:
                continue

            assoc_subnets = []
            is_main = False
            for assoc in rt.get("Associations", []) or []:
                if assoc.get("Main") is True:
                    is_main = True
                if assoc.get("SubnetId"):
                    assoc_subnets.append(assoc.get("SubnetId"))

            vpc_rts.append(
                {
                    "route_table_id": rt.get("RouteTableId"),
                    "name": _tag_value(rt.get("Tags"), "Name"),
                    "type": "public" if is_public_route_table(rt) else "private",
                    "main": is_main,
                    "associated_subnets": assoc_subnets,
                }
            )

        inventory.append(
            {
                "vpc_id": vpc_id,
                "name": _tag_value(vpc.get("Tags"), "Name"),
                "cidr": vpc.get("CidrBlock"),
                "is_default": vpc.get("IsDefault"),
                "internet_gateways": [x for x in vpc_igws if x],
                "subnets": sorted(vpc_subnets, key=lambda x: (x.get("visibility") or "", x.get("subnet_id") or "")),
                "route_tables": sorted(vpc_rts, key=lambda x: (x.get("type") or "", x.get("route_table_id") or "")),
            }
        )

    return {
        "meta": {
            "dump_utc": utc_ts(),
            "region": region or session.region_name,
            "service": "vpc",
        },
        "inventory": inventory,
    }


def main():
    # When executed from all.py, AWS_REGION/AWS_DEFAULT_REGION are propagated.
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")

    try:
        out = collect_vpc_inventory(region=region)
        print(json.dumps(out, ensure_ascii=False, indent=2, default=json_default))
    except ClientError as e:
        err = {
            "meta": {"dump_utc": utc_ts(), "region": region, "service": "vpc"},
            "ok": False,
            "error": {
                "type": "ClientError",
                "code": e.response.get("Error", {}).get("Code"),
                "message": e.response.get("Error", {}).get("Message"),
            },
        }
        print(json.dumps(err, ensure_ascii=False, indent=2, default=json_default))
    except Exception as e:
        err = {
            "meta": {"dump_utc": utc_ts(), "region": region, "service": "vpc"},
            "ok": False,
            "error": {"type": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(err, ensure_ascii=False, indent=2, default=json_default))


if __name__ == "__main__":
    main()