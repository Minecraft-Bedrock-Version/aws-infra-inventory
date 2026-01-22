from typing import Any, Dict, List

from normalizers.iam_user_normalizer import normalize_iam_users
from normalizers.iam_role_normalizer import normalize_iam_roles
from normalizers.network_normalizer import normalize_network
from normalizers.rds_normalizer import normalize_rds
from normalizers.sqs_normalizer import normalize_sqs
from normalizers.lambda_normalizer import normalize_lambda
from normalizers.ec2_normalizer import normalize_ec2

def run_normalizers(collected: Dict[str, Any]) -> Dict[str, Any]:

    account_id = collected["account_id"]
    region = collected["region"]
    collected_at = collected["collected_at"]

    all_nodes: List[Dict[str, Any]] = []

    iam_user_nodes = normalize_iam_users(
        collected["iam_users"], account_id
    )
    all_nodes.extend(iam_user_nodes)

    iam_role_nodes = normalize_iam_roles(
        collected["iam_roles"], account_id
    )
    all_nodes.extend(iam_role_nodes)

    network_nodes = normalize_network(
        collected["network"], account_id, region
    )
    all_nodes.extend(network_nodes)

    rds_nodes = normalize_rds(
        collected["rds"], account_id, region
    )
    all_nodes.extend(rds_nodes)

    sqs_nodes = normalize_sqs(
        collected["sqs"], account_id, region
    )
    all_nodes.extend(sqs_nodes)

    lambda_nodes = normalize_lambda(
        collected["lambda"], account_id, region
    )
    all_nodes.extend(lambda_nodes)
    
    ec2_nodes = normalize_ec2(
		    collected["ec2"], account_id, region
		)
		all_nodes.extend(ec2_nodes)

    normalized = {
        "schema_version": "1.0",
        "account_id": account_id,
        "region": region,
        "collected_at": collected_at,
        "nodes": all_nodes
    }

    return normalized
