from datetime import datetime, timezone

# 1. 서브넷 데이터 정규화 및 라우팅 테이블 매핑
def normalize_subnets(collected, account_id, region):
    nodes = []
    
    # 1-1. 서브넷 ID와 라우팅 테이블 ID 매핑 맵 생성
    subnet_to_rt = {}
    for rt_item in collected.get("route_tables", []):
        rt = rt_item["route_table"]
        rt_id = rt["RouteTableId"]
        
        for assoc in rt.get("Associations", []):
            if "SubnetId" in assoc:
                subnet_to_rt[assoc["SubnetId"]] = rt_id

    # 1-2. 개별 서브넷 정보 처리 및 노드 생성
    for item in collected.get("subnets", []):
        sn = item["subnet"]
        sn_id = sn["SubnetId"]
        
        # 태그에서 서브넷 이름(Name) 추출
        sn_name = None
        for tag in sn.get("Tags", []):
            if tag["Key"] == "Name":
                sn_name = tag["Value"]

        # 노드 구조 생성
        node = {
            "node_type": "subnet",
            "node_id": f"{account_id}:{region}:subnet:{sn_id}",
            "resource_id": sn_id,
            "name": sn_name,
            
            # 서브넷 속성 (VPC ID, CIDR, 가용영역, 라우팅 테이블 등)
            "attributes": {
                "vpc_id": sn.get("VpcId"),
                "cidr": sn.get("CidrBlock"),
                "az": sn.get("AvailabilityZone"),
                "visibility": "unknown", 
                "route_table_id": subnet_to_rt.get(sn_id)
            },
            
            # 메타데이터 정보
            "raw_refs": {
                "source": item.get("api_sources", ["ec2:DescribeSubnets"]),
                "collected_at": item.get("collected_at")
            }
        }
        
        nodes.append(node)

    return nodes
