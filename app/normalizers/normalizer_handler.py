from typing import Any, Dict, List

from normalizers.ec2_normalizer import normalize_ec2
from normalizers.lambda_normalizer import normalize_lambda
from normalizers.iam_user_normalizer import normalize_iam_users
from normalizers.iam_role_normalizer import normalize_iam_roles
from normalizers.sqs_normalizer import normalize_sqs
from normalizers.rds_normalizer import normalize_rds
from normalizers.vpc_normalizer import normalize_vpcs
from normalizers.subnet_normalizer import normalize_subnets
from normalizers.igw_normalizer import normalize_igws
from normalizers.route_table_normalizer import normalize_route_tables

def run_normalizers(collected: Dict[str, Any]) -> Dict[str, Any]:
    account_id = collected["account_id"]
    region = collected["region"]
    collected_at = collected["collected_at"]
    
    normalized_map = { #최종적으로 반환될 정규화 node들
        "schema_version": "1.0",
        "account_id": account_id,
        "region": region,
        "collected_at": collected_at,
        
        "ec2": {"nodes": normalize_ec2(collected.get("ec2", []), account_id, region)},
        "lambda": {"nodes": normalize_lambda(collected.get("lambda", []), account_id, region)},
        "iam_user": {"nodes": normalize_iam_users(collected.get("iam_user", []), account_id)},
        "iam_role": {"nodes": normalize_iam_roles(collected.get("iam_role", []), account_id)},
        "sqs": {"nodes": normalize_sqs(collected.get("sqs", []), account_id, region)},
        "rds": {"nodes": normalize_rds(collected.get("rds", []), account_id, region)},
        "vpc": {"nodes": normalize_vpcs(collected.get("vpc", []), account_id, region)},
        "subnet": {"nodes": normalize_subnets(collected.get("subnet", []), account_id, region)},
        "igw": {"nodes": normalize_igws(collected.get("igw", []), account_id, region)},
        "route_table": {"nodes": normalize_route_tables(collected.get("route_table", []), account_id, region)}
    }

    return normalized_map
