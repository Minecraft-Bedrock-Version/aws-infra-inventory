from datetime import datetime, timezone

def extract_name_from_tags(tags):
    if not tags: return None
    for tag in tags:
        if tag["Key"] == "Name":
            return tag["Value"]
    return None

def normalize_igws(collected, account_id, region):
    nodes = []
    # collected 자체가 이미 평탄화된 IGW 리스트입니다.
    items = collected

    for item in items:
        # AS-IS: igw = item["igw"] (에러 발생 지점)
        # TO-BE: item을 직접 사용
        igw = item
        igw_id = igw.get("InternetGatewayId")
        if not igw_id: continue # 방어 코드
        
        igw_name = extract_name_from_tags(igw.get("Tags", []))
        
        attachments = igw.get("Attachments", [])
        attached_vpc_id = attachments[0].get("VpcId") if attachments else None
        state = attachments[0].get("State") if attachments else "detached"

        node = {
            "node_type": "internet_gateway",
            "node_id": f"{account_id}:{region}:igw:{igw_id}",
            "resource_id": igw_id,
            "name": igw_name or igw_id,
            "attributes": {
                "attached_vpc_id": attached_vpc_id,
                "state": state
            },
            "raw_refs": {
                "source": item.get("api_sources", ["ec2:DescribeInternetGateways"]),
                "collected_at": item.get("collected_at")
            }
        }
        nodes.append(node)

    return nodes