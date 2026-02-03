def extract_paths(obj, prefix=""):
    paths = set()

    if isinstance(obj, dict): #node의 attributes가 딕셔너리인 경우
        for k, v in obj.items(): #딕셔너리의  키, 값을 분리해서
            new_prefix = f"{prefix}.{k}" if prefix else k #{현재_위치}.{키} 형식으로 경로 만들기
            paths.add(new_prefix) #경로에 추가
            paths |= extract_paths(v, new_prefix) #키의 값이 딕셔너리라면 재귀 호출

    elif isinstance(obj, list): #node의 attributes가 리스트인 경우
        for i, item in enumerate(obj): #i에 인덱스 값, item에 리스트 내용들을 넣음
            new_prefix = f"{prefix}[{i}]" #키 대신 인덱스로 경로 만들기 {현재_위치}.[{인덱스}]
            paths.add(new_prefix) #경로에 추가
            paths |= extract_paths(item, new_prefix) #리스트 내부 값이 딕셔너리라면 재귀 호출

    return paths #최종적으로 node의 attributes의 내용을 모두 불러옴 (경로 형식으로)

#update_raw_from_cli 함수에서 사용되는 map 
RAW_FIELD_MAP = { #정규화 node id의 내용을 raw의 필드로 매핑시키기 위한 map (cli node가 기존에 존재하는 서비스인 경우 기존 서비스는 raw data를 기준으로 edge를 만들기 때문에 cli node의 내용을 raw data에 덮어쓰게 하기 위함)
    "iam_user": { #아직 user만 구현
        "id_field": "UserName",
        "attributes": {
            "inline_policies": "InlinePolicies",
            "attached_policies": "AttachedPolicies",
            "group_policies": "GroupPolicies",
        }
    }
}

def update_raw_from_cli(raw_data: dict, final_node: dict) -> dict:
    node_type = final_node.get("node_type") #node의 type과
    resource_id = final_node.get("resource_id") #resource id,
    cli_attrs = final_node.get("attributes", {}) #속성을 각각 가져옴

    if node_type not in RAW_FIELD_MAP: #node type이 위에 정의한 map에 없으면
        return raw_data #그냥 raw data 반환

    mapping = RAW_FIELD_MAP[node_type] #존재하면 해당 map의 값을 가져와
    id_field = mapping["id_field"] 
    attr_map = mapping["attributes"]

    service_block = raw_data.get(node_type) #기존 리소스의 raw data의 type을 가져와서
    if not isinstance(service_block, dict):
        return raw_data

    items = ( #해당 type의 각 list 추출
        service_block.get("users") #현재 user만 구현
        # or service_block.get("roles")
        # or service_block.get("instances")
        # or service_block.get("functions")
        # or service_block.get("items")
    )

    if not isinstance(items, list):
        return raw_data

    for raw_obj in items: #해당 서비스의 내용을 읽어오면서
        if raw_obj.get(id_field) != resource_id:
            continue

        #cli의 각 필드를 raw data에 매핑하여 추가
        converted = {}
        for cli_key, raw_key in attr_map.items():
            if cli_key in cli_attrs:
                converted[raw_key] = cli_attrs[cli_key]

        if has_additional_fields_raw(converted, raw_obj): #raw data와 cli의 저장된 경로를 통해 추가되는 내용의 여부를 판단
            raw_obj.update(converted)
        else:
            for k, v in converted.items():
                if k not in raw_obj:
                    raw_obj[k] = v

    return raw_data


def has_additional_fields(cli_node: dict, original_node: dict) -> bool:
    cli_paths = extract_paths(cli_node.get("attributes", {})) #cli node의 attributes에 대한 경로 추출
    orig_paths = extract_paths(original_node.get("attributes", {})) #cli node와 중복되는 기존 node의 attributes에 대한 경로 추출

    #cli 경로에 기존 경로를 제외하여
    extra = cli_paths - orig_paths
    return bool(extra) #추가 경로가 있다면 True, 없다면 False 반환

def has_additional_fields_raw(cli_attrs: dict, raw_obj: dict) -> bool: #위 함수와 비슷한 동작
    cli_paths = extract_paths(cli_attrs)
    raw_paths = extract_paths(raw_obj)
    extra = cli_paths - raw_paths
    return bool(extra)

def handle_existing_resources(existing_cli_nodes: list, normalized_data: dict, raw_data: dict) -> dict:
    #기존 정규화 node
    original_node_map = {
        n["node_id"]: n
        for n in normalized_data.get("nodes", [])
    }

    updated_nodes_map = {}

    for cli_node in existing_cli_nodes:
        node_id = cli_node["node_id"]
        original_node = original_node_map.get(node_id)

        if not original_node:
            updated_nodes_map[node_id] = cli_node
            continue

        if has_additional_fields(cli_node, original_node):
            #cli의 데이터가 더 많으면 cli node로 덮어쓰기
            final_node = cli_node
        else:
            #아니라면 기존 내용에 cli 내용 추가
            merged = original_node.copy() 
            merged_attrs = original_node.get("attributes", {}).copy()
            merged_attrs.update(cli_node.get("attributes", {}))
            merged["attributes"] = merged_attrs
            final_node = merged
            
        for i, node in enumerate(normalized_data["nodes"]):
            if node["node_id"] == node_id:
                normalized_data["nodes"][i] = final_node

        updated_nodes_map[node_id] = final_node
        
        raw_data = update_raw_from_cli(raw_data, final_node)

    new_nodes = []
    for node in normalized_data.get("nodes", []):
        node_id = node["node_id"]
        if node_id in updated_nodes_map:
            new_nodes.append(updated_nodes_map[node_id])
        else:
            new_nodes.append(node)

    normalized_data["nodes"] = new_nodes

    return normalized_data, raw_data
