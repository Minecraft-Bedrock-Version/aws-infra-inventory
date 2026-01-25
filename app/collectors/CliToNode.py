import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _collapse_cli(cli_text: str) -> str:
    """
    - 줄바꿈 + 백슬래시(\)로 이어진 CLI를 한 줄로 정리
    - 불필요한 공백을 정리
    """
    # backslash newline 제거
    s = re.sub(r"\\\s*\n", " ", cli_text)
    # 나머지 줄바꿈을 공백으로
    s = re.sub(r"\s*\n\s*", " ", s)
    # 연속 공백 정리
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _extract_flag_value(cli_one_line: str, flag: str) -> Optional[str]:
    """
    --flag value 형태를 찾는다.
    value가 따옴표로 감싸졌든 아니든 처리.
    """
    # 1) 따옴표로 감싼 값: --flag '...'
    m = re.search(rf"{re.escape(flag)}\s+'([^']*)'", cli_one_line)
    if m:
        return m.group(1)

    # 2) 따옴표로 감싼 값: --flag "..."
    m = re.search(rf'{re.escape(flag)}\s+"([^"]*)"', cli_one_line)
    if m:
        return m.group(1)

    # 3) 일반 토큰 값: --flag token
    m = re.search(rf"{re.escape(flag)}\s+([^\s]+)", cli_one_line)
    if m:
        return m.group(1)

    return None


def _extract_policy_document(cli_text: str) -> str:
    """
    --policy-document ' {...} ' 또는 --policy-document "{...}" 에서 JSON 부분을 추출.
    정책 JSON 내부에는 공백/개행이 있을 수 있으므로, flag 이후 첫 따옴표부터 매칭.
    """
    s = _collapse_cli(cli_text)

    # 싱글쿼트로 감싼 JSON
    m = re.search(r"--policy-document\s+'(.+?)'\s*(?:--|$)", s)
    if m:
        return m.group(1).strip()

    # 더블쿼트로 감싼 JSON
    m = re.search(r'--policy-document\s+"(.+?)"\s*(?:--|$)', s)
    if m:
        return m.group(1).strip()

    # 따옴표 없이 들어온 경우(드묾): --policy-document { ... }
    m = re.search(r"--policy-document\s+(\{.+\})\s*(?:--|$)", s)
    if m:
        return m.group(1).strip()

    raise ValueError("CLI에서 --policy-document 값을 찾지 못했습니다.")


def _normalize_statement(stmt: Dict[str, Any]) -> Dict[str, Any]:
    """
    스키마에 맞게:
    - Effect: 그대로
    - Action: string이면 [string]으로
    - Resource: 스키마가 string이라
        - list 길이 1이면 단일 string
        - list 길이 >1이면 JSON 문자열로 저장(스키마 준수 목적)
    """
    effect = stmt.get("Effect")

    action = stmt.get("Action")
    if isinstance(action, list):
        action_list = action
    elif isinstance(action, str):
        action_list = [action]
    else:
        action_list = []

    resource = stmt.get("Resource")
    if isinstance(resource, list):
        if len(resource) == 1:
            resource_str = str(resource[0])
        else:
            resource_str = json.dumps(resource, ensure_ascii=False)
    elif resource is None:
        resource_str = ""
    else:
        resource_str = str(resource)

    return {
        "Effect": effect,
        "Action": action_list,
        "Resource": resource_str,
    }


def cli_put_user_policy_to_iam_user_json(
    cli_text: str,
    account_id: str = "string",
    collected_at: Optional[str] = None,
    source_tag: str = "cli:aws iam put-user-policy",
) -> Dict[str, Any]:
    """
    입력: aws iam put-user-policy ... (여러 줄/백슬래시 포함 가능)
    출력: 제공한 iam_user.json 스키마에 맞는 JSON(dict)

    NOTE:
    - arn/create_date는 CLI만으로는 보통 알 수 없어서 기본값 처리.
      (원하면 나중에 boto3로 get-user / list-user-policies 호출해서 채우는 방식으로 확장 가능)
    """
    collected_at = collected_at or _iso_now()

    cli_one = _collapse_cli(cli_text)

    # 명령어 검증(느슨하게)
    if "aws iam put-user-policy" not in cli_one:
        raise ValueError("이 변환기는 'aws iam put-user-policy' CLI만 지원합니다.")

    user_name = _extract_flag_value(cli_one, "--user-name")
    policy_name = _extract_flag_value(cli_one, "--policy-name")
    if not user_name:
        raise ValueError("CLI에서 --user-name 값을 찾지 못했습니다.")
    if not policy_name:
        raise ValueError("CLI에서 --policy-name 값을 찾지 못했습니다.")

    policy_doc_raw = _extract_policy_document(cli_text)
    try:
        policy_doc = json.loads(policy_doc_raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"policy-document JSON 파싱 실패: {e}") from e

    statements = policy_doc.get("Statement", [])
    if isinstance(statements, dict):
        statements = [statements]
    if not isinstance(statements, list):
        statements = []

    inline_policy_obj = {
        "PolicyName": policy_name,
        "Statement": [_normalize_statement(s) for s in statements if isinstance(s, dict)],
    }

    # node_id / resource_id 전략(팀 내에서 규칙 정하면 거기에 맞추면 됨)
    node_type = "iam_user"
    node_id = f"{node_type}:{account_id}:{user_name}"
    resource_id = user_name  # IAM User의 경우 이름을 리소스 식별자로 쓰는 전략

    out = {
        "schema_version": "1.0",
        "collected_at": collected_at,
        "account_id": account_id,
        "nodes": [
            {
                "node_type": node_type,        # resource_type_enum 자리
                "node_id": node_id,
                "resource_id": resource_id,
                "name": user_name,
                "attributes": {
                    "arn": "arn_string",        # CLI만으론 불명 -> 추후 boto3로 채우면 좋음
                    "create_date": collected_at,
                    "attached_policies": [],
                    "inline_policies": [inline_policy_obj],
                    "group_policies": [],
                },
                "raw_refs": {
                    "source": [source_tag],
                    "collected_at": collected_at,
                },
            }
        ],
    }

    return out