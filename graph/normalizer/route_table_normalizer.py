from datetime import datetime, timezone

# 1. 태그 리스트에서 Name 값 추출
def extract_name_from_tags(tags):
    if not tags: 
        return None
    
    for tag in tags:
        if tag["Key"] == "Name":
            return tag["Value"]
            
    return None


# 2. Route Table 데이터 정규화
def normalize_route_tables(collected, account_id, region):
    nodes = []
    collected_at = collected.get("collected_at") 

    for item in collected.get("route_tables", []):
        rt = item["route_table"]
        rt_id = rt["RouteTableId"]
        vpc_id = rt["VpcId"]
        
        # 메인 테이블 여부 및 연결된 서브넷 목록 파악
        main = False
        associated_subnets = []
        for assoc in rt.get("Associations", []):
            if assoc.get("Main"):
                is_main = True
            if "SubnetId" in assoc:
                associated_subnets.append(assoc["SubnetId"])

        # IGW 존재 여부에 따른 라우팅 테이블 타입 결정
        rt_type = "private"
        for route in rt.get("Routes", []):
            gateway_id = route.get("GatewayId", "")
            if gateway_id.startswith("igw-"):
                rt_type = "public"
                break

        # 노드 데이터 구조 생성
        node = {
            "node_type": "route_table",
            "node_id": f"{account_id}:{region}:rtb:{rt_id}",
            "resource_id": rt_id,
            "name": extract_name_from_tags(rt.get("Tags", [])),
            
            # 속성 정보
            "attributes": {
                "vpc_id": vpc_id,
                "type": rt_type,
                "main": is_main
            },
            
            # 관계 정보 
            "relationships": {
                "associated_subnets": associated_subnets,
                "vpc_id": vpc_id
            },
            
            # 메타데이터
            "raw_refs": {
                "source": ["ec2:DescribeRouteTables"],
                "collected_at": item.get("collected_at")
            }
        }
        
        nodes.append(node)

    return nodes
