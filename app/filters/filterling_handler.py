#node, edge에서 공격 탐지에 영향을 주는 필드만 추출

from datetime import datetime
from filters.filter import extract_connected_subgraph
from filters.ec2 import extract_ec2_for_vector
from filters.rds import extract_rds_for_vector
from filters.edge import extract_edges_for_vector
from filters.iam_role import extract_iam_role_for_vector 
from filters.iam_user import extract_iam_user_for_vector
from filters.igw import extract_igw_for_vector
from filters.lambda_filtering import extract_lambda_for_vector
from filters.route_table import extract_route_table_for_vector
from filters.sqs import extract_sqs_for_vector
from filters.subnet import extract_subnet_for_vector
from filters.vpc import extract_vpc_for_vector

def run_filtering(full_graph: dict, start_node_id: str) -> dict:
    #전체 node, edge를 가져와서 각각 nodes, edges에 넣어두고
    nodes = full_graph.get("nodes", [])
    edges = full_graph.get("edges", [])

    if not start_node_id: #시작 ndoe id가 안왔으면 빈 값 반환
        return {"nodes": [], "edges": []}
    
    #시작 node를 기준으로 간접, 직접 연결된 node와 edge들 추출
    subgraph = extract_connected_subgraph(graph_nodes=nodes, graph_edges=edges, start_node_id=start_node_id)
    
    refine_map = { #node의 type에 따라 필드를 정제하기 위한 매핑 리스트 생성해두고,
        "ec2_instance": extract_ec2_for_vector,
        "rds_instance": extract_rds_for_vector,
        "iam_role": extract_iam_role_for_vector,
        "iam_user": extract_iam_user_for_vector,
        "igw": extract_igw_for_vector,
        "lambda": extract_lambda_for_vector,
        "route_table": extract_route_table_for_vector,
        "sqs": extract_sqs_for_vector,
        "subnet": extract_subnet_for_vector,
        "vpc": extract_vpc_for_vector
    }
    
    final_nodes = []
    
    for node in subgraph.get("nodes", []): #node들을 순회하며
        node_type = node.get("node_type") #node의 type이
        if node_type in refine_map: #위에서 생성한 리스트에 포함된 type이라면
            refined = refine_map[node_type]({"nodes": [node]}) #해당 type에 맞는 함수를 실행하여 필드 정제
            final_nodes.extend(refined.get("nodes", [])) #정제된 node는 최종 node list에 저장
        else:
            final_nodes.append(node) #만약 위에서 생성한 리스트에 없는 type이면 그냥 최종 리스트에 저장해두기 -> 아마 이러면 정규화 노드가 그대로 들어감

    refined_edges_result = extract_edges_for_vector(subgraph) #edge 정제
    final_edges = refined_edges_result.get("edges", []) #정제된 edge들을 최종 edges list에 저장

    return { #schema version을 포함하여 node, edge 리스트 반환
        "schema_version": "1.5",
        "nodes": final_nodes,
        "edges": final_edges
    }