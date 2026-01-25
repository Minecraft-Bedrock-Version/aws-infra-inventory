from typing import Any, Dict, List

from app.normalizers.iam_user_normalizer import normalize_iam_users
from app.normalizers.iam_role_normalizer import normalize_iam_roles
from app.normalizers.rds_normalizer import normalize_rds
from app.normalizers.sqs_normalizer import normalize_sqs
from app.normalizers.lambda_normalizer import normalize_lambda
from app.normalizers.ec2_normalizer import normalize_ec2
from app.normalizers.igw_normalizer import normalize_igws
from app.normalizers.route_table_normalizer import normalize_route_tables
from app.normalizers.subnet_normalizer import normalize_subnets
from app.normalizers.vpc_normalizer import normalize_vpcs

def run_normalizers(collected: Dict[str, Any]) -> Dict[str, Any]:
    account_id = collected["account_id"]
    region = collected["region"]
    collected_at = collected["collected_at"]

    # 네트워크 데이터 뭉치 가져오기
    network_data = collected.get("network", {})

    normalized_map = {
        "schema_version": "1.0",
        "account_id": account_id,
        "region": region,
        "collected_at": collected_at,
        
        # 1. IAM은 최상위에 있으므로 기존 유지
        "iam_user": {"nodes": normalize_iam_users(collected.get("iam_users", []), account_id), "account_id": account_id, "collected_at": collected_at},
        "iam_role": {"nodes": normalize_iam_roles(collected.get("iam_roles", []), account_id), "account_id": account_id, "collected_at": collected_at},

        # 2. 네트워크 리소스는 network_data 내부의 키(vpcs, subnets 등)를 참조하도록 수정
        "vpc": {"nodes": normalize_vpcs(network_data.get("vpcs", []), account_id, region), "account_id": account_id, "collected_at": collected_at},
        "subnet": {"nodes": normalize_subnets(network_data.get("subnets", []), account_id, region), "account_id": account_id, "collected_at": collected_at},
        "igw": {"nodes": normalize_igws(network_data.get("igws", []), account_id, region), "account_id": account_id, "collected_at": collected_at},
        "route_table": {"nodes": normalize_route_tables(network_data.get("route_tables", []), account_id, region), "account_id": account_id, "collected_at": collected_at},

        # 3. 나머지도 실제 collected에 저장된 키 이름과 일치하는지 확인 (rds, sqs 등)
        "rds": {"nodes": normalize_rds(collected.get("rds", []), account_id, region), "account_id": account_id, "collected_at": collected_at},
        "sqs": {"nodes": normalize_sqs(collected.get("sqs", []), account_id, region), "account_id": account_id, "collected_at": collected_at},
        "lambda": {"nodes": normalize_lambda(collected.get("lambda", []), account_id, region), "account_id": account_id, "collected_at": collected_at},
        "ec2": {"nodes": normalize_ec2(collected.get("ec2", []), account_id, region), "account_id": account_id, "collected_at": collected_at}
    }

    return normalized_map