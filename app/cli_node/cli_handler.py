"""
AWS CLI Normalization Handler

다양한 AWS 서비스(IAM, EC2 등)의 CLI 명령어를 파싱하여 
시각화에 필요한 노드 및 에지 데이터로 정규화하는 메인 핸들러입니다.
"""
    
from cli_node.comparator import compare_with_existing
from cli_node import iam_cli
from cli_node import ec2_cli
import shlex


class AWSNormalizationHandler:
    def __init__(self):
        # 서비스별 파서(Parser) 등록
        # 각 서비스 모듈의 parse 함수는 CLI 명령어를 파싱하여
        # action (생성, 업데이트 등), identifier (리소스 고유 식별자),
        # 그리고 params (추가 메타데이터)를 반환합니다.
        self.handlers = {
            'iam': iam_cli.parse_iam, # IAM 서비스 CLI 파서
            'ec2': ec2_cli.parse_ec2  # EC2 서비스 CLI 파서
        }


    def process(self, cli_input, existing_nodes):
        service, parts = classify_service(cli_input) #CLI에서 서비스 추출 및 JSON 추출
        
        if service not in self.handlers: #지원하지 않는 서비스는 에러 반환 (UI에서 1차적으로 지원하지 않는 서비스에 대한 CLI 생성을 막아두긴 했지만 혹시 모를 오타, 수동 변경으로 인한 에러 예외처리)
            return {"error": f"Unsupported service: {service}"}

        action, identifier, params = self.handlers[service](parts) #분류된 서비스에 맞는 handler 실행

        existing_node = compare_with_existing(service, identifier, existing_nodes) #기존 인프라와 비교

        if existing_node:
            return {
                "type": "UPDATE",
                "node_id": existing_node['id'],
                "action": action,
                "updates": params
            }
        else:
            return {
                "type": "CREATE",
                "node_data": {
                    "id": f"n_{len(existing_nodes) + 1}",
                    "service": service,
                    "identifier": identifier,
                    "action": action,
                    "metadata": params
                }
            }
            
def classify_service(cli_input):
    try:
        #따옴표로 감싸진 JSON 문자열을 하나의 인자로 저장
        parts = shlex.split(cli_input)
        if len(parts) < 2 or parts[0] != 'aws':
            return None, None
        return parts[1], parts
    except ValueError:
        return None, None