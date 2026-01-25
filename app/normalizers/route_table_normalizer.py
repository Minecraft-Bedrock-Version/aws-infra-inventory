from datetime import datetime, timezone

def extract_name_from_tags(tags):
    if not tags: return None
    for tag in tags:
        if tag["Key"] == "Name":
            return tag["Value"]
    return None

def normalize_route_tables(collected, account_id, region):
    nodes = []
    # collected 자체가 이제 평탄화된 Route Table 리스트입니다.
    items = collected

    for item in items:
        # AS-IS: rt = item["route_table"] (에러 발생 지점)
        # TO-BE: item을 직접 사용
        rt = item
        rt_id = rt.get("RouteTableId")
        if not rt_id: continue # 데이터가 아닌 경우 방어
        
        vpc_id = rt.get("VpcId")
        
        is_main = False
        associated_subnets = []
        for assoc in rt.get("Associations", []):
            if assoc.get("Main"):
                is_main = True
            if "SubnetId" in assoc:
                associated_subnets.append(assoc["SubnetId"])

        # Public/Private 판별 로직
        rt_type = "private"
        for route in rt.get("Routes", []):
            gateway_id = route.get("GatewayId", "")
            if gateway_id.startswith("igw-"):
                rt_type = "public"
                break

        node = {
            "node_type": "route_table",
            "node_id": f"{account_id}:{region}:rtb:{rt_id}",
            "resource_id": rt_id,
            "name": extract_name_from_tags(rt.get("Tags", [])),
            "attributes": {
                "vpc_id": vpc_id,
                "type": rt_type,
                "main": is_main
            },
            "relationships": {
                "associated_subnets": associated_subnets,
                "vpc_id": vpc_id
            },
            "raw_refs": {
                "source": ["ec2:DescribeRouteTables"],
                "collected_at": item.get("collected_at")
            }
        }
        nodes.append(node)

    return nodes