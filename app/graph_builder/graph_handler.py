import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import json

from graph_builder.ec2_graph import graph_ec2
from graph_builder.lambda_graph import graph_lambda
from graph_builder.iam_user_graph import graph_user
from graph_builder.iam_role_graph import graph_role
# from graph_builder.igw_graph import transform_igw_to_graph
# from graph_builder.rds_graph import transform_rds_to_graph
# from graph_builder.route_table_graph import transform_route_table_to_graph
# from graph_builder.subnet_graph import transform_subnet_to_graph
# from graph_builder.vpc_graph import transform_vpc_to_graph
# from graph_builder.sqs_graph import transform_sqs_to_graph

def run_graph_builder(collected: Dict[str, Any], normalized_map: Dict[str, Any]) -> Dict[str, Any]:
    account_id = collected["account_id"]
    region = collected["region"]
    collected_at = collected["collected_at"]

    normalized_map.setdefault("edges", [])
    normalized_map["edges"].extend(graph_ec2(collected, account_id, region))
    normalized_map["edges"].extend(graph_lambda(collected, account_id, region))
    normalized_map["edges"].extend(graph_user(collected, account_id, region))
    normalized_map["edges"].extend(graph_role(collected, account_id, region))

    return normalized_map