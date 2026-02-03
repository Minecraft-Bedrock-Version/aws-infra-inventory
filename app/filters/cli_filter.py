def run_cli_filter(existing_graph: dict, cli_graph: dict):

    #기존 노드에서 Node ID만 추출해서 리스트로 만들기
    existing_node_ids = {
        node["node_id"] #node id만 가져와서
        for node in existing_graph.get("nodes", []) #리스트에 넣음
        if "node_id" in node
    }

    result = { #결과 리스트 미리 만들어두기
        "existing": [],
        "new": []
    }

    #CLI Node id가 기존 Node id 리스트에 있는 값인지 확인
    cli_nodes = cli_graph.get("nodes", []) #CLI graph 구조에서 nodes 내용 추출
    for cli_node in cli_nodes:
        cli_node_id = cli_node.get("node_id") #node id만 추출

        if cli_node_id in existing_node_ids: #만약 기존 node id 리스트에 cli nod id가 존재하면
            result["existing"].append(cli_node) #existing에 추가
        else:
            cli_node["is_cli"] = True #Graph 단계에서 정규화 포맷을 대상으로 edge 생성이 이뤄져야 하기 때문에 cli 노드라는 표식을 남김
            result["new"].append(cli_node) #new에 추가

    return result #최종 리스트 반환
