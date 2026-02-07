#lambda handler에서 호출하는 함수
def handle_existing_resources(existing_cli_nodes: list, normalized_data: dict, raw_data: dict) -> dict:
    original_node_map = { #기존 정규화 Node들의 node id를 모두 추출
        n["node_id"]: n
        for n in normalized_data.get("nodes", [])
    }

    updated_nodes_map = {}

    for cli_node in existing_cli_nodes: #cli node들을 순회 (근데 보통 1개만 존재)
        node_id = cli_node["node_id"] #Node id를 추출
        original_node = original_node_map.get(node_id) #기존 정규화 Node들의 node id 중에서 cli node의 id와 같은 값을 추출

        if not original_node: #만약 기존 node들 중에 cli node와 id가 같은 값이 없다면
            updated_nodes_map[node_id] = cli_node #cli ndoe를 그대로 업데이트하고
            continue #종료

        merged = original_node.copy() #기존 node를 복사하여
        merged_attrs = original_node.get("attributes", {}).copy() #속성 값 추출

        #인라인 정책이 cli node 속성에 존재한다면
        if "inline_policies" in cli_node.get("attributes", {}):
            old = merged_attrs.get("inline_policies", []) #기존 정규화 node에 존재하던 인라인 정책 속성을 old 변수에 담아두고,
            new = cli_node["attributes"]["inline_policies"] #cli node의 인라인 정책 속성을 new 변수에 담아서
            merged_attrs["inline_policies"] = merge_inline_policies(old, new) #인라인 정책을 병합하여 응답 반환

        #관리형 정책이 cli node 속성에 존재한다면
        if "attached_policies" in cli_node.get("attributes", {}):
            old = merged_attrs.get("attached_policies", []) #기존 정규화 node에 존재하던 관리형 정책 속성을 old 변수에 담아두고,
            new = cli_node["attributes"]["attached_policies"] #cli node의 관리형 정책 속성을 new 변수에 담아서
            merged_attrs["attached_policies"] = merge_attached_policies(old, new) #관리형 정책을 병합하여 반환

        merged["attributes"] = merged_attrs #병합된 관리형 정책과, 추가된 인라인 정책 반환
        final_node = merged #최종 final_node에 병합된 정책들을 포함하여 반환

        for i, node in enumerate(normalized_data["nodes"]): #기존 정규화 노드의 인덱스 번호와 노드들을 i, node 변수에 담으며 순회
            if node["node_id"] == node_id: #만약 node의 id가 cli node의 id와 같다면
                normalized_data["nodes"][i] = final_node #최종적으로 반환되는 정규화 데이터에 해당 인덱스 값을 가진 노드를 cli 기준으로 최종 병합된 노드로 교체

        updated_nodes_map[node_id] = final_node #update node에도 final node 추가
        raw_data = update_raw_from_cli(raw_data, final_node) #edge 생성 단계에서도 사용되기 위해 raw data도 업데이트

    normalized_data["nodes"] = [
        updated_nodes_map.get(n["node_id"], n)
        for n in normalized_data.get("nodes", [])
    ]

    return normalized_data, raw_data

#User에게 추가된 정책이 무엇인지 분류 (AWS 관리형 또는 고객 관리형)
def classify_policy_arn(arn: str) -> str:
    if arn.startswith("arn:aws:iam::aws:policy/"): #arn:aws:iam::aws:policy/aws-service-role/정책명 과 같은 형식 == AWS 관리형
        return "aws_managed"
    elif ":policy/" in arn: #arn:aws:iam::계정id:policy/정책명 과 같은 형식 == 고객 관리형
        return "customer_managed"
    return "unknown"

#기존 정규화 node와 cli node의 관리형 정책을 merge
def merge_attached_policies(old: list, new: list) -> list:
    old = old or [] #기존 정규화 node
    new = new or [] #CLI Node

    #PolicyArn 기준으로 병합 (중복은 제거)
    merged = {p["PolicyArn"]: p for p in old + new}

    return list(merged.values())

#기존 정규화 node와 cli node의 인라인 정책을 merge
def merge_inline_policies(old: list, new: list) -> list:
    old = old or [] #기존 정규화 node
    new = new or [] #CLI Node

    #PolicyName을 기준으로 병합 (중복은 새로운 값으로 덮어쓰기 -> 인라인 정책은 중복된 값이 존재하는 경우 새로 추가된 정책으로 덮어쓰기함)
    merged = {p["PolicyName"]: p for p in old}
    for p in new:
        merged[p["PolicyName"]] = p

    return list(merged.values())

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

#정규화된 cli node 토대로 기존 인프라의 raw data 업데이트 
def update_raw_from_cli(raw_data: dict, final_node: dict) -> dict:
    node_type = final_node.get("node_type") #CLI Node에서 node type과
    name = final_node.get("name") #name,
    cli_attrs = final_node.get("attributes", {}) #속성값 추출

    if node_type not in RAW_FIELD_MAP: #node type이 매핑용 필드에 존재하지 않으면 raw data 그냥 반환
        return raw_data

    mapping = RAW_FIELD_MAP[node_type] #매핑용 딕셔너리에서 CLI Node의 Node type과 일치하는 필드 추출
    id_field = mapping["id_field"] #raw rield map의 id_field 필드와
    attr_map = mapping["attributes"] #attributes 필드의 내용 추출

    service_block = raw_data.get(node_type) #raw data에서 CLI Node type에 해당하는 node 추출
    if not isinstance(service_block, dict):
        return raw_data

    if service_block.get("users"): #node의 users의 값이 존재하면
        items = service_block.get("users") #해당 값을 items에 저장
        if not isinstance(items, list):
            return raw_data

        for raw_obj in items: #각 필드를 순회하며
            if raw_obj.get(id_field) != name: #id_filed의 값이 name과 다르다면 continue (CLI User만 아래 과정 진행)
                continue

            converted = {}
            for cli_key, raw_key in attr_map.items():
                if cli_key in cli_attrs: #raw field map의 정규화 필드명이 cli 속성값에 존재한다면
                    converted[raw_key] = cli_attrs[cli_key] #raw field map에 매핑된대로 정규화 -> raw용 필드로 변경

            for k, v in converted.items(): #raw용 필드를 k에, 해당 필드의 내용을 v에 담아가며 순회

                if k == "InlinePolicies": #k가 인라인 정책인 경우
                    old = raw_obj.get(k, []) #기존 raw data의 인라인 정책을 모두 가져와 old에 담고,
                    raw_obj[k] = merge_inline_policies(old, v) #같은 이름의 정책은 cli 내용으로 덮어쓰기, 다른 이름의 정책은 추가
                    continue

                if k == "AttachedPolicies": #k가 관리형 정책인 경우
                    old = raw_obj.get(k, []) #기존 raw data의 관리형 정책을 모두 가져와 old에 담고,
                    raw_obj[k] = merge_attached_policies(old, v) #같은 ARN의 정책은 유지, 다른 ARN의 정책은 추가
                    continue

                #Group Policy는 CLI 기준으로 덮어쓰기
                raw_obj[k] = v

    return raw_data