from datetime import datetime, timezone

# 1. 태그 리스트에서 Name 값 추출
def extract_name_from_tags(tags):
    if not tags:
        return None

    for tag in tags:
        if tag["Key"] == "Name":
            return tag["Value"]

    return None


# 2. VPC 데이터 노드 생성
def normalize_vpcs(collected, account_id, region):
    nodes = []

    for item in collected.get("vpcs", []):
        vpc = item["vpc"]
        vpc_id = vpc["VpcId"]
        
        # 태그에서 VPC 이름 추출
        vpc_name = extract_name_from_tags(vpc.get("Tags", []))

        node = {
            "node_type": "vpc",
            "node_id": f"{account_id}:{region}:vpc:{vpc_id}",
            "resource_id": vpc_id,
            "name": vpc_name,

            # VPC 고유 속성 (네트워크 범위 및 기본 여부)
            "attributes": {
                "cidr": vpc.get("CidrBlock"),
                "default": vpc.get("IsDefault", False),
                "internet_gateway_id": None
            },

            # 데이터 출처 및 수집 정보
            "raw_refs": {
                "source": item.get("api_sources", ["ec2:DescribeVpcs"]),
                "collected_at": item.get("collected_at")
            }
        }
        
        nodes.append(node)

    return nodes
