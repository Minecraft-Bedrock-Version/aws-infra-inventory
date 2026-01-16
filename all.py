#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError


def json_default(o: Any):
    """JSON 직렬화 불가 객체 처리 (datetime 등)"""
    try:
        return str(o)
    except Exception:
        return repr(o)



def utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def local_run_id() -> str:
    """
    Local time run folder name.
    Format: 26y01m15d0342c (yy y MM m dd d HHMM c)
    """
    now = datetime.now()
    return now.strftime("%y") + "y" + now.strftime("%m") + "m" + now.strftime("%d") + "d" + now.strftime("%H%M") + "c"


def paginated_call(client, op_name: str, result_key: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    paginator 지원 API면 전 페이지를 합쳐 반환.
    result_key가 있으면 해당 리스트를 합치고, 없으면 페이지별 원본을 pages로 저장.
    """
    try:
        paginator = client.get_paginator(op_name)
    except Exception:
        # paginator 미지원이면 단발 호출
        resp = getattr(client, op_name)(**kwargs)
        return {"op": op_name, "mode": "single", "response": resp}

    pages = paginator.paginate(**kwargs)

    if result_key:
        merged: List[Any] = []
        raw_pages: List[Dict[str, Any]] = []
        for page in pages:
            raw_pages.append(page)
            if result_key in page and isinstance(page[result_key], list):
                merged.extend(page[result_key])
        return {
            "op": op_name,
            "mode": "paginated_merge",
            "result_key": result_key,
            "items": merged,
            "raw_pages": raw_pages,  # "전체" 보존을 위해 페이지 원본도 같이 저장
        }

    raw_pages = [p for p in pages]
    return {"op": op_name, "mode": "paginated_pages", "pages": raw_pages}


def safe_call(fn, label: str) -> Dict[str, Any]:
    """권한/리전 미지원 등 에러가 나도 스크립트 전체는 계속 진행"""
    try:
        return {"ok": True, "label": label, "data": fn()}
    except ClientError as e:
        return {
            "ok": False,
            "label": label,
            "error": {
                "type": "ClientError",
                "code": e.response.get("Error", {}).get("Code"),
                "message": e.response.get("Error", {}).get("Message"),
            },
        }
    except Exception as e:
        return {"ok": False, "label": label, "error": {"type": type(e).__name__, "message": str(e)}}


def run_extra_scripts(project_dir: Path, output_dir: Path, region: str) -> Dict[str, Any]:
    """
    Run additional .py scripts (e.g., separate IAM dump scripts) found in the project directory.
    We auto-detect scripts whose filename starts with 'iam' (case-insensitive), excluding this all.py.
    Each script is executed with:
      - cwd=output_dir (so relative outputs land next to our files)
      - env OUTPUT_DIR set to output_dir (for scripts that support it)
      - env RUN_TS set to the current run timestamp folder name
      - AWS_REGION propagated
    Returns a summary dict suitable for saving into a JSON 'extras' file.
    """
    results: Dict[str, Any] = {"region": region, "scripts": []}

    # Detect extra scripts (iam*.py) next to all.py
    candidates = sorted(
        [
            p for p in project_dir.glob("iam*.py")
            if p.is_file() and p.name != "all.py"
        ],
        key=lambda p: p.name.lower(),
    )

    for script in candidates:
        script_result: Dict[str, Any] = {"script": script.name, "ok": True}

        env = os.environ.copy()
        # Ensure child scripts (iam*.py etc.) use the same region as this run.
        env["AWS_REGION"] = region
        env["AWS_DEFAULT_REGION"] = region
        env["OUTPUT_DIR"] = str(output_dir)
        env["RUN_TS"] = output_dir.parent.name  # folder name like 20260115T061612Z

        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(output_dir),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            script_result["returncode"] = proc.returncode
            script_result["stdout"] = proc.stdout
            script_result["stderr"] = proc.stderr

            # Try to parse stdout as JSON for separate saving later
            try:
                if proc.stdout and proc.stdout.strip():
                    script_result["stdout_json"] = json.loads(proc.stdout)
                else:
                    script_result["stdout_json"] = None
            except Exception:
                script_result["stdout_json"] = None

            if proc.returncode != 0:
                script_result["ok"] = False
        except Exception as e:
            script_result["ok"] = False
            script_result["error"] = {"type": type(e).__name__, "message": str(e)}

        results["scripts"].append(script_result)

    return results

def dump_region(region: str) -> Dict[str, Any]:
    session = boto3.Session(region_name=region)

    out: Dict[str, Any] = {
        "meta": {
            "dump_utc": utc_ts(),
            "region": region,
        },
        "services": {},
    }

    # =========================
    # EC2 (인스턴스 + VPC 관련 대부분은 EC2 API에서 나옴)
    # =========================
    ec2 = session.client("ec2")
    out["services"]["ec2"] = {
        "describe_instances": safe_call(lambda: paginated_call(ec2, "describe_instances"), "ec2.describe_instances"),
        "describe_vpcs": safe_call(lambda: paginated_call(ec2, "describe_vpcs", "Vpcs"), "ec2.describe_vpcs"),
        "describe_subnets": safe_call(lambda: paginated_call(ec2, "describe_subnets", "Subnets"), "ec2.describe_subnets"),
        "describe_security_groups": safe_call(
            lambda: paginated_call(ec2, "describe_security_groups", "SecurityGroups"),
            "ec2.describe_security_groups",
        ),
        "describe_route_tables": safe_call(
            lambda: paginated_call(ec2, "describe_route_tables", "RouteTables"),
            "ec2.describe_route_tables",
        ),
        "describe_network_acls": safe_call(
            lambda: paginated_call(ec2, "describe_network_acls", "NetworkAcls"),
            "ec2.describe_network_acls",
        ),
        "describe_internet_gateways": safe_call(
            lambda: paginated_call(ec2, "describe_internet_gateways", "InternetGateways"),
            "ec2.describe_internet_gateways",
        ),
        "describe_nat_gateways": safe_call(
            lambda: paginated_call(ec2, "describe_nat_gateways", "NatGateways"),
            "ec2.describe_nat_gateways",
        ),
        "describe_network_interfaces": safe_call(
            lambda: paginated_call(ec2, "describe_network_interfaces", "NetworkInterfaces"),
            "ec2.describe_network_interfaces",
        ),
    }

    # =========================
    # Lambda
    # =========================
    lam = session.client("lambda")
    out["services"]["lambda"] = {
        "list_functions": safe_call(lambda: paginated_call(lam, "list_functions", "Functions"), "lambda.list_functions"),
        # Event source mappings도 전체 수집(예: SQS 트리거)
        "list_event_source_mappings": safe_call(
            lambda: paginated_call(lam, "list_event_source_mappings", "EventSourceMappings"),
            "lambda.list_event_source_mappings",
        ),
    }

    # =========================
    # SQS
    # =========================
    sqs = session.client("sqs")
    sqs_block: Dict[str, Any] = {}
    sqs_block["list_queues"] = safe_call(lambda: sqs.list_queues(), "sqs.list_queues")

    # 큐 URL 목록을 얻었으면, 각 큐의 Attribute를 전부(All) 받아서 같이 저장
    def fetch_all_queue_attrs():
        resp = sqs.list_queues()
        urls = resp.get("QueueUrls", [])
        all_attrs = []
        for url in urls:
            attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["All"])
            all_attrs.append({"QueueUrl": url, "Attributes": attrs.get("Attributes", {})})
        return {"queues": urls, "attributes": all_attrs}

    sqs_block["get_queue_attributes_all"] = safe_call(fetch_all_queue_attrs, "sqs.get_queue_attributes(All)")
    out["services"]["sqs"] = sqs_block

    # =========================
    # S3 (글로벌 목록 + 버킷별 위치 정도)
    # =========================
    # Use the same session/region for consistency (S3 list_buckets is global but keeping one session avoids confusion)
    s3 = session.client("s3")
    s3_block: Dict[str, Any] = {}
    s3_block["list_buckets"] = safe_call(lambda: s3.list_buckets(), "s3.list_buckets")

    def fetch_bucket_locations():
        resp = s3.list_buckets()
        buckets = [b["Name"] for b in resp.get("Buckets", [])]
        results = []
        for name in buckets:
            try:
                loc = s3.get_bucket_location(Bucket=name)
                results.append({"Bucket": name, "LocationConstraint": loc.get("LocationConstraint")})
            except ClientError as e:
                results.append({
                    "Bucket": name,
                    "error": {
                        "code": e.response.get("Error", {}).get("Code"),
                        "message": e.response.get("Error", {}).get("Message"),
                    }
                })
        return results

    s3_block["get_bucket_location"] = safe_call(fetch_bucket_locations, "s3.get_bucket_location")
    out["services"]["s3"] = s3_block

    # =========================
    # RDS
    # =========================
    rds = session.client("rds")
    out["services"]["rds"] = {
        "describe_db_instances": safe_call(
            lambda: paginated_call(rds, "describe_db_instances", "DBInstances"),
            "rds.describe_db_instances",
        ),
        "describe_db_subnet_groups": safe_call(
            lambda: paginated_call(rds, "describe_db_subnet_groups", "DBSubnetGroups"),
            "rds.describe_db_subnet_groups",
        ),
    }

    return out


def main():
    # 필요하면 여기서 리전을 여러 개로 늘릴 수 있음
    regions = [
        # Default to us-east-1 unless AWS_REGION is explicitly set in the environment.
        os.environ.get("AWS_REGION", "us-east-1"),
    ]

    project_dir = Path(__file__).resolve().parent

    out_root = "aws_dump_output"
    os.makedirs(out_root, exist_ok=True)

    run_ts = local_run_id()
    # Create a per-run folder to avoid mixing files from different executions
    run_dir = os.path.join(out_root, run_ts)
    os.makedirs(run_dir, exist_ok=True)

    saved_paths: List[str] = []

    for region in regions:
        region_dump = dump_region(region)

        # Save per-service files under aws_dump_output/<run_ts>/<region>/
        region_dir = os.path.join(run_dir, region)
        os.makedirs(region_dir, exist_ok=True)

        services = region_dump.get("services", {})
        for service_name, service_payload in services.items():
            service_doc = {
                "meta": {
                    "dump_utc": run_ts,
                    "region": region,
                    "service": service_name,
                },
                "data": service_payload,
            }

            service_path = os.path.join(region_dir, f"{service_name}_{run_ts}.json")
            with open(service_path, "w", encoding="utf-8") as f:
                json.dump(service_doc, f, ensure_ascii=False, indent=2, default=json_default)

            saved_paths.append(service_path)

        # Also save a small manifest for the region
        manifest = {
            "meta": {
                "dump_utc": run_ts,
                "region": region,
            },
            "services": sorted(list(services.keys())),
        }
        manifest_path = os.path.join(region_dir, f"manifest_{run_ts}.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2, default=json_default)

        saved_paths.append(manifest_path)

        # Run extra scripts (e.g., IAM dump scripts) and save ONLY actual IAM output files, not extras_* logs.
        extras_summary = run_extra_scripts(project_dir=project_dir, output_dir=Path(region_dir), region=region)

        for s in extras_summary.get("scripts", []):
            script_name = s.get("script", "unknown.py")
            script_stem = os.path.splitext(script_name)[0]

            stdout_json = s.get("stdout_json")
            if stdout_json is not None:
                out_path = os.path.join(region_dir, f"{script_stem}_{run_ts}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(stdout_json, f, ensure_ascii=False, indent=2, default=json_default)
                saved_paths.append(out_path)

    print("[OK] Saved files:")
    for p in saved_paths:
        print(" -", p)


if __name__ == "__main__":
    main()