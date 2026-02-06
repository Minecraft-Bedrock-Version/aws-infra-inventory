"""
EC2 CLI Parser

EC2 CLI 명령어를 파싱하여 노드 데이터를 생성합니다.
ai_web-ui의 EC2Handler에서 생성된 CLI 명령어를 파싱합니다.
"""

import re
import json


# EC2 지원 명령어 목록
EC2_COMMANDS = [
    # 인스턴스 관련
    "run-instances",
    "start-instances",
    "stop-instances",
    "terminate-instances",
    "reboot-instances",
    "describe-instances",
    # 이미지 관련
    "describe-images",
    "create-image",
    "deregister-image",
    # 보안 그룹
    "create-security-group",
    "delete-security-group",
    "authorize-security-group-ingress",
    "authorize-security-group-egress",
    "revoke-security-group-ingress",
    "revoke-security-group-egress",
    # 키 페어
    "create-key-pair",
    "delete-key-pair",
    "describe-key-pairs",
    # VPC
    "create-vpc",
    "delete-vpc",
    "describe-vpcs",
    # 서브넷
    "create-subnet",
    "delete-subnet",
    "describe-subnets",
    # 볼륨
    "create-volume",
    "delete-volume",
    "attach-volume",
    "detach-volume",
    # 태그
    "create-tags",
    "delete-tags",
]


def parse_ec2(parts):
    """
    EC2 CLI 명령어를 분석하여 리소스 동작과 설정을 추출합니다.
    
    Args:
        parts: shlex.split()를 거친 CLI 입자의 리스트
    
    Returns:
        tuple: (action, identifier, params)
    """
    if len(parts) < 3:
        return None, None, {}
    
    action = parts[2]
    params = {}
    
    # 1. 지원되는 명령어인지 확인
    if action not in EC2_COMMANDS:
        print(f"[WARNING] 처리 불가능한 EC2 명령어입니다: {action}")
        return action, None, {}
    
    # 2. CLI 플래그(--옵션) 파싱
    # --key value 또는 --flag 형태를 처리합니다.
    i = 3
    while i < len(parts):
        if parts[i].startswith('--'):
            # kebab-case 플래그를 snake_case 키로 변환 (예: --instance-type -> instance_type)
            key = parts[i].lstrip('-').replace('-', '_')
            
            # 다음 인자가 있고 다음 옵션의 시작이 아니라면 해당 값을 사용
            if i + 1 < len(parts) and not parts[i + 1].startswith('--'):
                value = parts[i + 1]
                
                # JSON 문자열인 경우 객체/리스트로 디코딩 (ex: tag-specifications)
                if value.strip().startswith('{') or value.strip().startswith('['):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass
                
                params[key] = value
                i += 2
            else:
                # 불리언 플래그인 경우 (ex: --associate-public-ip-address)
                params[key] = True
                i += 1
        else:
            i += 1
    
    # 3. 리소스의 고유 식별자(이름 또는 ID)를 추출
    # 기존 노드와 비교하거나 새 노드를 생성할 때 id 생성용으로 사용됩니다.
    identifier = _extract_identifier(action, params)
    
    return action, identifier, params


def _extract_identifier(action, params):
    """
    다양한 EC2 명령어 파라미터 중에서 가장 적합한 리소스 식별자를 찾아냅니다.
    """
    # 우선순위 1: 태그 설정 내의 Name 키 값 (사용자가 직접 정한 이름)
    tag_specs = params.get('tag_specifications')
    if tag_specs:
        name = _extract_name_from_tag_specs(tag_specs)
        if name:
            return name
    
    # 우선순위 2: 인스턴스 ID 리스트
    instance_ids = params.get('instance_ids')
    if instance_ids:
        if isinstance(instance_ids, list):
            return instance_ids[0] if instance_ids else None
        return instance_ids
    
    # 우선순위 3: 기타 주요 리소스 ID 필드들
    identifiers = [
        'security_group_id',
        'group_id',
        'group_name',
        'key_name',
        'vpc_id',
        'subnet_id',
        'volume_id',
        'image_id',
    ]
    
    for key in identifiers:
        if key in params:
            return params[key]
    
    return None


def _extract_name_from_tag_specs(tag_specs):
    """
    tag-specifications 구조체 내부에서 'Name' 태그를 찾아 값을 반환합니다.
    """
    # AWS CLI 스타일의 문자열 포맷 지원
    if isinstance(tag_specs, str):
        match = re.search(r'Key=Name,Value=([^\}\]]+)', tag_specs)
        if match:
            return match.group(1).strip()
    
    # JSON 객체 스타일 지원
    elif isinstance(tag_specs, list):
        for spec in tag_specs:
            if isinstance(spec, dict):
                tags = spec.get('Tags', [])
                for tag in tags:
                    if tag.get('Key') == 'Name':
                        return tag.get('Value')
    
    return None


def parse_run_instances_detail(params):
    """
    run-instances 명령어의 상세 파라미터를 추출합니다.
    ai_web-ui EC2Handler에서 생성하는 형식에 맞춤.
    
    Returns:
        dict: 정제된 EC2 인스턴스 설정
    """
    return {
        'region': params.get('region'),
        'image_id': params.get('image_id'),
        'instance_type': params.get('instance_type'),
        'key_name': params.get('key_name'),
        'public_ip': params.get('associate_public_ip_address', False),
        'metadata_options': params.get('metadata_options'),
        'block_device_mappings': params.get('block_device_mappings'),
        'tag_specifications': params.get('tag_specifications'),
    }
