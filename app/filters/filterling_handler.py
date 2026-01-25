from datetime import datetime
from app.filters.filter import extract_connected_subgraph
from app.filters.ec2 import extract_ec2_for_vector
from app.filters.rds import extract_rds_for_vector
from app.filters.edge import extract_edges_for_vector
from app.filters.iam_role import extract_iam_role_for_vector 
from app.filters.iam_user import extract_iam_user_for_vector
from app.filters.igw import extract_igw_for_vector
from app.filters.lambda_filtering import extract_lambda_for_vector
from app.filters.route_table import extract_route_table_for_vector
from app.filters.sqs import extract_sqs_for_vector
from app.filters.subnet import extract_subnet_for_vector
from app.filters.vpc import extract_vpc_for_vector

def run_filtering(full_graph: dict, start_node_id: str) -> dict:

    subgraph = extract_connected_subgraph(
        graph_nodes=full_graph.get("nodes", []),
        graph_edges=full_graph.get("edges", []),
        start_node_id=start_node_id
    )
    
    refine_map = {
        "ec2_instance": extract_ec2_for_vector,
        "rds_instance": extract_rds_for_vector,
        "iam_role": extract_iam_role_for_vector,
        "iam_user": extract_iam_user_for_vector,
        "internet_gateway": extract_igw_for_vector,
        "lambda_function": extract_lambda_for_vector,
        "route_table": extract_route_table_for_vector,
        "sqs": extract_sqs_for_vector,
        "subnet": extract_subnet_for_vector,
        "vpc": extract_vpc_for_vector
    }

    final_nodes = []
    
    for node in subgraph.get("nodes", []):
        node_type = node.get("type")
        if node_type in refine_map:
            refined = refine_map[node_type]({"nodes": [node]})
            final_nodes.extend(refined.get("nodes", []))
        else:
            final_nodes.append(node)

    refined_edges_result = extract_edges_for_vector(subgraph)
    final_edges = refined_edges_result.get("edges", [])

    return {
        "schema_version": "1.0",
        "collected_at": datetime.now().isoformat(),
        "account_id": full_graph.get("account_id", "unknown"),
        "nodes": final_nodes,
        "edges": final_edges
    }