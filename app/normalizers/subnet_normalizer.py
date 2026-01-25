from datetime import datetime, timezone

def normalize_subnets(collected, account_id, region):
    nodes = []
    
    # [수정 1] collected 데이터가 이미 평탄화되었으므로 
    # Route Table 관련 정보는 run_normalizers에서 따로 넘겨받거나 
    # 혹은 이 함수가 서브넷 리스트만 받는다면 이 로직은 별도로 분리되어야 합니다.
    # (현재 구조상 collected에 subnet 데이터만 들어온다면 아래 rt 루프는 skip되거나 오류가 날 수 있음)
    
    subnet_to_rt = {}
    # 만약 collected 안에 route_table 데이터도 섞여서 들어오는 구조라면:
    for rt_item in collected:
        # rt_item이 route_table 정보인지 확인 후 처리
        if "RouteTableId" in rt_item:
            rt = rt_item
            rt_id = rt["RouteTableId"]
            for assoc in rt.get("Associations", []):
                if "SubnetId" in assoc:
                    subnet_to_rt[assoc["SubnetId"]] = rt_id

    # [수정 2] 실제 서브넷 노드 생성 루프
    for item in collected:
        # item["subnet"] 대신 item을 직접 사용
        sn = item
        sn_id = sn.get("SubnetId")
        if not sn_id: continue # 서브넷 데이터가 아닌 경우 skip
        
        sn_name = None
        for tag in sn.get("Tags", []):
            if tag["Key"] == "Name":
                sn_name = tag["Value"]

        node = {
            "node_type": "subnet",
            "node_id": f"{account_id}:{region}:subnet:{sn_id}",
            "resource_id": sn_id,
            "name": sn_name or sn_id,
            "attributes": {
                "vpc_id": sn.get("VpcId"),
                "cidr": sn.get("CidrBlock"),
                "az": sn.get("AvailabilityZone"),
                "visibility": "unknown", 
                "route_table_id": subnet_to_rt.get(sn_id)
            },
            "raw_refs": {
                "source": item.get("api_sources", ["ec2:DescribeSubnets"]),
                "collected_at": item.get("collected_at")
            }
        }
        nodes.append(node)

    return nodes