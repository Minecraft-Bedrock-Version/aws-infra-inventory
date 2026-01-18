import boto3
import base64
import json
import re
from datetime import datetime

# 날짜 형식을 JSON으로 변환하기 위한 핸들러
def datetime_handler(x):
    if isinstance(x, datetime):
        return x.isoformat()
    raise TypeError(f"Object of type {type(x).__name__} is not JSON serializable")

def collect_resources():
    ec2_client = boto3.client('ec2', region_name='us-east-1')
    
    try:
        # EC2 인스턴스 목록 및 키 페어 정보 가져오기
        instances_response = ec2_client.describe_instances()
        key_pairs_response = ec2_client.describe_key_pairs()
    except Exception:
        return

    all_instances = []
    # UserData에서 SQS URL과 RDS 엔드포인트를 찾기 위한 정규식 패턴
    sqs_pattern = r"https://sqs\.us-east-1\.amazonaws\.com/[^\s'\"]+"
    rds_pattern = r"[^\s'\"/]+\.us-east-1\.rds\.amazonaws\.com"

    for reservation in instances_response.get('Reservations', []):
        for instance in reservation.get('Instances', []):
            instance_info = instance.copy()
            
            # 검색 결과 초기값 설정
            instance_info['sqs_info'] = {"detected": False, "queue_url": None}
            instance_info['rds_info'] = {"detected": False, "db_endpoint": None}

            # 인스턴스의 UserData 가져오기 및 분석
            try:
                attr = ec2_client.describe_instance_attribute(
                    InstanceId=instance['InstanceId'], 
                    Attribute='userData'
                )
                
                if 'UserData' in attr and 'Value' in attr['UserData']:
                    user_data_raw = base64.b64decode(attr['UserData']['Value']).decode('utf-8', errors='ignore')
                    
                    # 1. SQS 매칭 확인
                    sqs_match = re.search(sqs_pattern, user_data_raw)
                    if sqs_match:
                        instance_info['sqs_info'] = {
                            "detected": True,
                            "queue_url": sqs_match.group(0)
                        }

                    # 2. RDS 매칭 확인
                    rds_match = re.search(rds_pattern, user_data_raw)
                    if rds_match:
                        instance_info['rds_info'] = {
                            "detected": True,
                            "db_endpoint": rds_match.group(0)
                        }
            except Exception:
                pass

            all_instances.append(instance_info)

    final_output = {
        "meta": {
            "collected_at": datetime.now().isoformat(),
            "region": "us-east-1",
            "version": "v3.0_full_data"
        },
        "data": {
            "ec2_instances": all_instances,
            "key_pairs": key_pairs_response.get('KeyPairs', [])
        }
    }

    output_file = 'ec2.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, default=datetime_handler, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    collect_resources()
