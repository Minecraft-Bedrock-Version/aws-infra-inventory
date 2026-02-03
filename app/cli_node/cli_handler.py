# from cli_node.CliToNode import cli_put_user_policy_to_iam_user_json

# def run_cli_collector(cli_input: str, account_id: str) -> dict:

#     if not cli_input or cli_input.strip() == "":
#         return {"nodes": [], "edges": []}
    
#     try:
        
#         cli_node_result = cli_put_user_policy_to_iam_user_json(
#             cli_text=cli_input,
#             account_id=account_id
#         )
#         return cli_node_result
        
#     except Exception as e:
#         print(f"CLI 변환 중 오류 발생: {e}")
#         return {"nodes": [], "edges": []}
    
from cli_node.comparator import compare_with_existing
from cli_node.iam_cli import iam_handler            
import shlex


class AWSNormalizationHandler:
    def __init__(self):
        self.handlers = { #서비스 분류
            'iam': iam_handler.parse_iam
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

# 테스트 실행
if __name__ == "__main__":
    handler = AWSNormalizationHandler()
    mock_db = [{"id": "n_1", "service": "iam", "identifier": "admin-user"}]

    print(handler.process("aws iam create-user --user-name new-user", mock_db))
    print(handler.process("aws iam update-user --user-name admin-user", mock_db))