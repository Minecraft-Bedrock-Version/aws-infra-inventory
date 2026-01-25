from datetime import datetime, timezone

def extract_name_from_tags(tags):
    if not tags: return None
    for tag in tags:
        if tag["Key"] == "Name":
            return tag["Value"]
    return None

def normalize_vpcs(collected, account_id, region):
    nodes = []

    for item in collected:
        vpc = item 
        
        vpc_id = vpc.get("VpcId")
        if not vpc_id: continue # 방어 코드 추가
        
        vpc_name = extract_name_from_tags(vpc.get("Tags", []))

        node = {
            "node_type": "vpc",
            "node_id": f"{account_id}:{region}:vpc:{vpc_id}",
            "resource_id": vpc_id,
            "name": vpc_name or vpc_id, # 이름이 없으면 ID라도 표시
            "attributes": {
                "cidr": vpc.get("CidrBlock"), 
                "default": vpc.get("IsDefault", False),
                "internet_gateway_id": None 
            },
            "raw_refs": {
                "source": item.get("api_sources", ["ec2:DescribeVpcs"]),
                "collected_at": item.get("collected_at")
            }
        }
        nodes.append(node)

    return nodes