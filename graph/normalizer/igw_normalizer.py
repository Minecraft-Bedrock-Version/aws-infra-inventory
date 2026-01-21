from datetime import datetime, timezone

# 1. 태그 리스트에서 'Name' 값 추출 유틸리티
def extract_name_from_tags(tags):
    if not tags:
        return None

    for tag in tags:
        if tag["Key"] == "Name":
            return tag["Value"]

    return None


# 2. Internet Gateway 데이터 정규화 (VPC 연결 상태 및 ID 추출)
def normalize_igws(collected, account_id, region):
    nodes = []

    for item in collected.get("igws", []):
        igw = item["igw"]
        igw_id = igw["InternetGatewayId"]
        igw_name = extract_name_from_tags(igw.get("Tags", []))
        
        # IGW 연결 정보 추출 (첫 번째 연결된 VPC 기준)
        attachments = igw.get("Attachments", [])
        attached_vpc_id = attachments[0].get("VpcId") if attachments else None
        state = attachments[0].get("State") if attachments else "detached"

        # 노드 구조 생성
        node = {
            "node_type": "internet_gateway",
            "node_id": f"{account_id}:{region}:igw:{igw_id}",
            "resource_id": igw_id,
            "name": igw_name,

            # IGW 고유 속성 (연결된 VPC 및 연결 상태)
            "attributes": {
                "attached_vpc_id": attached_vpc_id,
                "state": state
            },

            # 메타데이터
            "raw_refs": {
                "source": item.get("api_sources", ["ec2:DescribeInternetGateways"]),
                "collected_at": item.get("collected_at")
            }
        }
        
        nodes.append(node)

    return nodes
