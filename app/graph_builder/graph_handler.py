import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import json

# 1. 개별 리소스 빌더 임포트
from app.graph_builder.iam_user_graph import transform_iam_users
from app.graph_builder.iam_role_graph import transform_iam_roles
from app.graph_builder.igw_graph import transform_igw_to_graph
from app.graph_builder.ec2_graph import transform_ec2_to_graph
from app.graph_builder.rds_graph import transform_rds_to_graph
from app.graph_builder.route_table_graph import transform_route_table_to_graph
from app.graph_builder.subnet_graph import transform_subnet_to_graph
from app.graph_builder.vpc_graph import transform_vpc_to_graph
from app.graph_builder.lambda_graph import transform_lambda_to_graph
from app.graph_builder.sqs_graph import transform_sqs_to_graph

def safe_node(n):
    if not n: return None
    if isinstance(n, dict): return n
    try:
        curr = n
        for _ in range(3):
            if isinstance(curr, (str, bytes)):
                curr = json.loads(curr)
            else:
                break
        return curr if isinstance(curr, dict) else None
    except:
        return None

class GraphAssembler:
    def __init__(self):
        self.transformer_map = {
            "iam_user": transform_iam_users,
            "iam_role": transform_iam_roles,
            "igw": transform_igw_to_graph,
            "ec2": transform_ec2_to_graph,
            "rds": transform_rds_to_graph,
            "route_table": transform_route_table_to_graph,
            "sqs": transform_sqs_to_graph,
            "lambda": transform_lambda_to_graph,
            "subnet": transform_subnet_to_graph,
            "vpc": transform_vpc_to_graph
        }

    def assemble(self, normalized_data_map: Dict[str, Any], cli_graph: Dict[str, Any] = None) -> Dict[str, Any]:
        master_nodes = {}
        master_edges = {}
        account_id = str(normalized_data_map.get("account_id", "288528695623"))

        # 1. 인프라 데이터 수집 및 ID 강제 변환
        for key, data in normalized_data_map.items():
            if key in ["account_id", "region", "collected_at", "schema_version"]:
                continue
            
            current_data = safe_node(data)
            while isinstance(current_data, (str, bytes)):
                try:
                    # 따옴표가 겹쳐있는 경우를 위해 성공할 때까지 계속 json.loads 시도
                    current_data = json.loads(current_data)
                except:
                    break # 더 이상 풀 수 없으면 중단
                
            if not isinstance(current_data, dict):
                print(f"DEBUG: Skipping [{key}] because data is still {type(current_data)}")
                continue
            
            if "nodes" not in current_data:
                # 가끔 데이터가 {"lambda": {"nodes": [...]}} 처럼 들어오는 경우
                if key in current_data and isinstance(current_data[key], dict):
                    current_data = current_data[key]
                else:
                    continue

            # 트랜스포머 실행
            func = self.transformer_map.get(key)
            if func:
                try:
                    res_graph = func(current_data)
                    nodes_added = 0
                    for n in res_graph.get("nodes", []):
                        if n.get("name") == "scp-test":
                            n["id"] = f"iam_user:{account_id}:scp-test"
                        
                        n_id = n.get("id")
                        if n_id:
                            master_nodes[n_id] = n
                            nodes_added += 1
                    
                    for e in res_graph.get("edges", []):
                        if e.get("id"): master_edges[e["id"]] = e
                    
                    print(f"DEBUG: Transformer for [{key}] produced {nodes_added} nodes.")
                except Exception as e:
                    print(f"DEBUG: Error in transformer [{key}]: {e}")
                    continue

        # 2. CLI 그래프 병합 (이제 ID가 같으므로 scp-test 노드에 정책이 합쳐짐)
        if cli_graph and cli_graph.get("nodes"):
            for cli_node in cli_graph["nodes"]:
                # CLI 노드의 ID는 이미 iam_user:288528695623:scp-test 형식임
                c_id = cli_node.get("node_id")
                
                if c_id in master_nodes:
                    # 인프라 노드에 CLI에서 온 정책 정보를 덮어씌움
                    master_nodes[c_id].setdefault("attributes", {}).update(cli_node.get("attributes", {}))
                else:
                    # 만약 인프라에 없었다면 새로 추가 (안전장치)
                    master_nodes[c_id] = self._convert_to_node_schema(cli_node, account_id)

                # 엣지 생성 (관계 확장)
                new_edges = self._create_edges_and_placeholders(cli_node, master_nodes, account_id)
                for e in new_edges:
                    master_edges[e["id"]] = e
                    
        service_edges = self._link_role_to_services(master_nodes, master_edges)
        for e in service_edges:
            master_edges[e["id"]] = e

        # EC2 -> IGW 연결 (public EC2인 경우)
        ec2_igw_edges = self._link_public_ec2_to_igw(master_nodes)
        for e in ec2_igw_edges:
            master_edges[e["id"]] = e

        # User -> Role 연결 (assume 권한이 있으면)
        user_role_edges = self._link_users_to_assumable_roles(master_nodes)
        for e in user_role_edges:
            master_edges[e["id"]] = e

        # Role -> 실제 리소스 연결 (정책 Resource 기반, Service 중간 계층 없음)
        role_resource_edges = self._link_roles_to_services(master_nodes)
        for e in role_resource_edges:
            master_edges[e["id"]] = e

        # 디버깅용 로그: 이제 여기에 'Executes'와 'InSubnet'이 떠야 합니다!
        from collections import Counter
        edge_types = Counter([e.get('relation') for e in master_edges.values()])
        print(f"DEBUG: Edge Distribution: {dict(edge_types)}")
        
        return {
            "nodes": list(master_nodes.values()),
            "edges": list(master_edges.values()),
            "account_id": account_id,
            "collected_at": datetime.now().isoformat()
        }
    def _convert_to_node_schema(self, node: Dict[str, Any], account_id: str) -> Dict[str, Any]:
        """정규화 포맷 노드를 최종 Node Schema로 변환"""
        node_id = node.get("node_id") or node.get("id")
        # node_id에서 region 추출 (형식: account:region:type:id)
        parts = node_id.split(":")
        region = parts[1] if len(parts) > 1 else "global"

        return {
            "id": node_id,
            "type": node.get("node_type") or node.get("type"),
            "name": node.get("name", "Unknown"),
            "arn": node.get("attributes", {}).get("arn", ""),
            "region": region,
            "properties": {
                **node.get("attributes", {}),
                "source": node.get("raw_refs", {}).get("source", [])
            }
        }

    def _create_edges_and_placeholders(self, cli_node: Dict[str, Any], master_nodes: Dict[str, Any], account_id: str) -> List[Dict[str, Any]]:
        generated_edges = []
        src_id = cli_node.get("node_id")
        src_label = f"{cli_node.get('node_type')}:{cli_node.get('name')}"
        
        # 리소스 타입별 매칭 가능한 서비스 접두사 정의
        service_map = {
            "rds_instance": "rds",
            "rds": "rds",
            "sqs": "sqs",
            "lambda_function": "lambda",
            "lambda": "lambda",
            "ec2_instance": "ec2",
            "ec2": "ec2",
            "iam_role": "iam",
            "iam_user": "iam"
        }

        inline_policies = cli_node.get("attributes", {}).get("inline_policies", [])
        for policy in inline_policies:
            for stmt in policy.get("Statement", []):
                resource_arn = stmt.get("Resource")
                actions = stmt.get("Action", [])
                if isinstance(actions, str): actions = [actions]
                
                if not resource_arn: continue

                # [핵심] Resource가 "*" 인 경우 Action 분석 후 매칭
                if resource_arn == "*":
                    for target_id, target_node in master_nodes.items():
                        if target_id == src_id: continue
                        
                        target_type = target_node.get("type", "").lower()
                        service_prefix = service_map.get(target_type)
                        if not service_prefix: continue
                        
                        is_match = any(act == "*" or act.startswith(f"{service_prefix}:") or act == f"{service_prefix}:*" for act in actions)
                        
                        if is_match:
                            # [필터링 강화] 대상이 IAM Role인 경우 sts:AssumeRole 권한이 없으면 Edge 생성 안 함
                            if service_prefix == "iam" and target_node.get("type") == "iam_role":
                                can_assume = any(act in ["*", "sts:AssumeRole", "sts:*"] for act in actions)
                                if not can_assume:
                                    continue # 단순 조회 권한(Get/List)이면 연결 건너뜀

                            relation = "CanAssumeRole" if service_prefix == "iam" else "AllowAccess"
                            edge_id = f"edge:{src_id}:{relation}:{target_id}"
                            generated_edges.append({
                                "id": edge_id,
                                "relation": relation,
                                "src": src_id,
                                "dst": target_id,
                                "conditions": actions 
                            })
                    continue

                arns = resource_arn if isinstance(resource_arn, list) else [resource_arn]
                for arn in arns:
                    # 1. 기존 노드 중 ARN 매칭 확인
                    dst_node = next((n for n in master_nodes.values() if n.get("arn") == arn), None)
                    
                    # 2. 없으면 가상 노드(Placeholder) 생성
                    if not dst_node:
                        dst_node = self._create_placeholder_node(arn, account_id)
                        master_nodes[dst_node["id"]] = dst_node

                    # 3. 엣지 생성
                    relation = f"{stmt.get('Effect', 'Allow')}Access"
                    edge_id = f"edge:{src_id}:{relation}:{dst_node['id']}"
                    
                    generated_edges.append({
                        "id": edge_id,
                        "relation": relation,
                        "src": src_id,
                        "src_label": src_label,
                        "dst": dst_node["id"],
                        "dst_label": f"{dst_node['type']}:{dst_node['name']}",
                        "directed": True,
                        "conditions": stmt.get("Action", [])
                    })
        return generated_edges

    def _create_placeholder_node(self, arn: str, account_id: str) -> Dict[str, Any]:
        """ARN을 분석하여 존재하지 않는 리소스를 위한 가상 노드 생성"""
        # ARN 파싱 (arn:aws:service:region:account:resource)
        parts = arn.split(":")
        service = parts[2] if len(parts) > 2 else "unknown"
        region = parts[3] if len(parts) > 3 and parts[3] else "global"
        
        # 이름 추출 (마지막 섹션의 / 이후)
        res_name = parts[-1].split("/")[-1] if parts else "Unknown-Resource"
        
        # 우리 팀의 ID 규칙 적용
        virtual_id = f"{account_id}:{region}:{service}:{res_name}"
        
        return {
            "id": virtual_id,
            "type": service,
            "name": res_name,
            "arn": arn,
            "region": region,
            "properties": {
                "status": "placeholder",
                "exists_in_infra": False,
                "reason": "Created from CLI policy reference"
            }
        }

    # --- 기존 Merge 헬퍼 함수들 (유지) ---
    def _merge_graph_to_master(self, master_nodes, master_edges, sub_graph):
        for n in sub_graph.get("nodes", []):
            n_id = n.get("id")
            master_nodes[n_id] = self._merge_nodes(master_nodes.get(n_id, {}), n)
        for e in sub_graph.get("edges", []):
            e_id = e.get("id")
            master_edges[e_id] = self._merge_edges(master_edges.get(e_id, {}), e)

    def _merge_nodes(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(old)
        for key in ["type", "name", "arn", "region"]:
            if not merged.get(key) and new.get(key):
                merged[key] = new[key]
        old_props = old.get("properties", {})
        new_props = new.get("properties", {})
        merged_props = {**old_props}
        for k, v in new_props.items():
            if k not in merged_props:
                merged_props[k] = v
            else:
                merged_props[k] = self._merge_property_value(merged_props[k], v)
        merged["properties"] = merged_props
        return merged

    def _merge_property_value(self, old_value: Any, new_value: Any) -> Any:
        if isinstance(old_value, dict) and isinstance(new_value, dict):
            merged = dict(old_value)
            for k, v in new_value.items():
                merged[k] = self._merge_property_value(merged.get(k), v) if k in merged else v
            return merged
        if isinstance(old_value, list) and isinstance(new_value, list):
            return list(set(map(str, old_value)) | set(map(str, new_value)))
        return new_value

    def _merge_edges(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        merged = {**old, **new}
        return merged

    def _link_role_to_services(self, master_nodes, master_edges):
        edges = []
        node_list = list(master_nodes.values())
        
        print("\n--- [DEBUG] Starting Linker (Enhanced) ---")
        all_types = set(str(n.get("type")).lower() for n in node_list)
        print(f"DEBUG: Available types in master_nodes: {all_types}")

        for node in node_list:
            props = node.get("properties", {})
            n_id = node.get("id")
            n_type = str(node.get("type")).lower()
            
            # 1. Lambda -> Role 연결 (Executes)
            if "lambda" in n_type:
                # 여러 키 후보군을 체크합니다.
                role_arn = props.get("role_arn") or props.get("role") or props.get("RoleArn")
                if role_arn:
                    # ARN이 일치하는 Role 노드 찾기
                    target_role = next((rn for rn in node_list if rn.get("type") == "iam_role" and rn.get("arn") == role_arn), None)
                    if target_role:
                        print(f"DEBUG: >>> SUCCESS! Linked Role [{target_role.get('name')}] to Lambda [{node.get('name')}]")
                        edges.append({
                            "id": f"edge:{target_role['id']}:Executes:{n_id}",
                            "src": target_role['id'],
                            "dst": n_id,
                            "relation": "Executes"
                        })

            # 2. Service -> Subnet 연결 (InSubnet)
            # Lambda(subnets 리스트), EC2(subnet_id), RDS(db_subnet_group 내 ID) 등 대응
            sub_id = props.get("subnet_id") or props.get("SubnetId")
            sub_list = props.get("subnets", [])
            
            # 만약 sub_list가 딕셔너리 형태(RDS 등)라면 ID만 추출
            if isinstance(sub_list, dict):
                sub_list = sub_list.get("Subnets", [])
            
            target_sn_ids = sub_list if isinstance(sub_list, list) else ([sub_id] if sub_id else [])
            
            for sn_id in target_sn_ids:
                # sn_id가 딕셔너리인 경우(RDS subnet group 등) id 문자열만 추출
                actual_sn_id = sn_id.get("SubnetIdentifier") if isinstance(sn_id, dict) else sn_id
                
                if not actual_sn_id: continue

                # Subnet 노드 찾기
                target_sn = next((sn for sn in node_list if sn.get("type") == "subnet" and actual_sn_id in sn.get("id", "")), None)
                if target_sn:
                    print(f"DEBUG: >>> SUCCESS! Linked {n_type} to Subnet [{actual_sn_id}]")
                    edges.append({
                        "id": f"edge:{n_id}:InSubnet:{target_sn['id']}",
                        "src": n_id,
                        "dst": target_sn['id'],
                        "relation": "InSubnet"
                    })
        
        print("--- [DEBUG] Linker Finished ---\n")
        return edges

    def _link_public_ec2_to_igw(self, master_nodes):
        """Public EC2 인스턴스를 해당 VPC의 IGW와 연결"""
        edges = []
        node_list = list(master_nodes.values())
        
        print("\n--- [DEBUG] Starting EC2-IGW Linker ---")
        
        for node in node_list:
            n_type = str(node.get("type")).lower()
            if "ec2" not in n_type:
                continue
            
            props = node.get("properties", {})
            n_id = node.get("id")
            
            # public=true이고 vpc_id가 있어야 함
            if not props.get("public") or not props.get("vpc_id"):
                print(f"DEBUG: EC2 [{node.get('name')}] - public={props.get('public')}, vpc_id={props.get('vpc_id')}")
                continue
            
            vpc_id = props.get("vpc_id")
            print(f"DEBUG: Looking for IGW in VPC [{vpc_id}] for EC2 [{node.get('name')}]")
            
            # IGW의 attached_vpc_id와 비교
            target_igw = next((igw for igw in node_list 
                             if igw.get("type") == "internet_gateway" 
                             and igw.get("properties", {}).get("attached_vpc_id") == vpc_id), None)
            
            if target_igw:
                print(f"DEBUG: >>> SUCCESS! Linked EC2 [{node.get('name')}] to IGW [{target_igw.get('name')}]")
                edges.append({
                    "id": f"edge:{n_id}:CONNECTED_TO_IGW:{target_igw['id']}",
                    "src": n_id,
                    "dst": target_igw['id'],
                    "relation": "CONNECTED_TO_IGW",
                    "directed": False,
                    "conditions": [
                        {
                            "ec2": {
                                "attributes": {
                                    "public": True
                                }
                            }
                        }
                    ]
                })
            else:
                print(f"DEBUG: >>> FAILED! No IGW found for VPC [{vpc_id}]")
        
        print("--- [DEBUG] EC2-IGW Linker Finished ---\n")
        return edges

    def _link_ec2_to_igw(self, master_nodes):
        """EC2 인스턴스가 public이면 해당 VPC의 IGW와 연결"""
        edges = []
        node_list = list(master_nodes.values())
        
        print("\n--- [DEBUG] Starting EC2-IGW Linker ---")
        
        for node in node_list:
            n_type = str(node.get("type")).lower()
            if "ec2" not in n_type:
                continue
            
            props = node.get("properties", {})
            n_id = node.get("id")
            
            # public 속성과 vpc_id 확인
            is_public = props.get("public", False)
            vpc_id = props.get("vpc_id")
            
            if not is_public or not vpc_id:
                continue
            
            # 같은 VPC에 연결된 IGW 찾기
            target_igw = next((igw for igw in node_list 
                             if igw.get("type") == "internet_gateway" 
                             and vpc_id in igw.get("id", "")), None)
            
            if target_igw:
                print(f"DEBUG: >>> SUCCESS! Linked EC2 [{node.get('name')}] to IGW [{target_igw.get('name')}]")
                edges.append({
                    "id": f"edge:{n_id}:CONNECTED_TO_IGW:{target_igw['id']}",
                    "src": n_id,
                    "dst": target_igw['id'],
                    "relation": "CONNECTED_TO_IGW",
                    "directed": False,
                    "conditions": [
                        {
                            "ec2": {
                                "attributes": {
                                    "public": True
                                }
                            }
                        }
                    ]
                })
        
        print("--- [DEBUG] EC2-IGW Linker Finished ---\n")
        return edges
    
    def _link_users_to_assumable_roles(self, master_nodes):
        """
        User -> Role 엣지 생성 (데이터 경로 수정본)
        """
        edges = []
        node_list = list(master_nodes.values())
        
        print("\n--- [DEBUG] Starting User-Role Linker ---")
        
        # 1. 노드 필터링 (node_type과 type 둘 다 체크)
        user_nodes = [n for n in node_list if str(n.get("node_type") or n.get("type")).lower() == "iam_user"]
        role_nodes = [n for n in node_list if str(n.get("node_type") or n.get("type")).lower() == "iam_role"]
        
        print(f"DEBUG: Found {len(user_nodes)} users and {len(role_nodes)} roles")
        
        for user in user_nodes:
            # node_id와 name 추출
            user_id = user.get("node_id") or user.get("id")
            user_name = user.get("name")
            
            # [수정] properties 대신 attributes에서 inline_policies를 가져옴
            user_attrs = user.get("attributes") or user.get("properties") or {}
            policies = user_attrs.get("inline_policies", [])
            
            for policy in policies:
                statements = policy.get("Statement", [])
                for stmt in statements:
                    # Action 확인
                    actions = stmt.get("Action", [])
                    if isinstance(actions, str): actions = [actions]
                    
                    # sts:AssumeRole 권한 검사
                    has_assume_role = any(
                        action in ["sts:AssumeRole", "sts:*", "*", "iam:*"] 
                        for action in actions
                    )
                    
                    if not has_assume_role:
                        continue
                    
                    # Resource 확인
                    resources = stmt.get("Resource", [])
                    if isinstance(resources, str): resources = [resources]
                    
                    for resource in resources:
                        if resource == "*":
                            # 모든 Role에 연결
                            for role in role_nodes:
                                role_id = role.get("node_id") or role.get("id")
                                role_name = role.get("name")
                                
                                edge_id = f"edge:{user_id}:CAN_ASSUME_ROLE:{role_id}"
                                edges.append({
                                    "id": edge_id,
                                    "src": user_id,
                                    "src_label": f"iam_user:{user_name}",
                                    "dst": role_id,
                                    "dst_label": f"iam_role:{role_name}",
                                    "relation": "CAN_ASSUME_ROLE",
                                    "directed": True,
                                    "conditions": [
                                        {
                                            "iam_user": {
                                                "attributes": {"policies": {"inline_policies": [policy]}},
                                                "statement": stmt
                                            }
                                        }
                                    ]
                                })
                                print(f"DEBUG: User [{user_name}] can assume ALL roles")
                        else:
                            # 특정 Role ARN 매칭
                            for role in role_nodes:
                                if role.get("arn") == resource:
                                    role_id = role.get("node_id") or role.get("id")
                                    role_name = role.get("name")
                                    
                                    edge_id = f"edge:{user_id}:CAN_ASSUME_ROLE:{role_id}"
                                    edges.append({
                                        "id": edge_id,
                                        "src": user_id,
                                        "src_label": f"iam_user:{user_name}",
                                        "dst": role_id,
                                        "dst_label": f"iam_role:{role_name}",
                                        "relation": "CAN_ASSUME_ROLE",
                                        "directed": True,
                                        "conditions": [
                                            {
                                                "iam_user": {
                                                    "attributes": {"policies": {"inline_policies": [policy]}},
                                                    "statement": stmt
                                                }
                                            }
                                        ]
                                    })
                                    print(f"DEBUG: User [{user_name}] can assume role [{role_name}]")
        
        print(f"--- [DEBUG] User-Role Linker Finished (generated {len(edges)} edges) ---\n")
        return edges
    
    def _link_roles_to_services(self, master_nodes):
        """
        Role의 정책(inline/attached)에서 실제 리소스 접근 권한이 있으면 Role -> 리소스 엣지 생성
        Service 중간 계층 없이 직접 Role -> 실제 리소스로 연결
        """
        edges = []
        node_list = list(master_nodes.values())
        
        print("\n--- [DEBUG] Starting Role-Resource Linker ---")
        
        # Role 노드 찾기
        role_nodes = [n for n in node_list if str(n.get("type")).lower() == "iam_role"]
        
        print(f"DEBUG: Found {len(role_nodes)} roles")
        
        for role in role_nodes:
            role_id = role.get("id")
            role_name = role.get("name")
            
            props = role.get("properties", {})
            
            # 분석할 정책들 수집 (inline + attached)
            all_policies = []
            
            # Inline policies (리스트가 아닐 수도 있으니 안전하게 처리)
            inline_policies = props.get("inline_policies", [])
            if isinstance(inline_policies, list):
                all_policies.extend(inline_policies)
                inline_count = len(inline_policies)
            else:
                inline_policies = []
                inline_count = 0
            
            # Attached policies (생략된 경우도 있을 수 있음)
            attached_policies = props.get("attached_policies", [])
            if isinstance(attached_policies, list):
                all_policies.extend(attached_policies)
                attached_count = len(attached_policies)
            else:
                attached_policies = []
                attached_count = 0
            
            print(f"DEBUG: Role [{role_name}] has {inline_count} inline + {attached_count} attached policies")
            
            # 정책 분석: 서비스별 액션 및 리소스 그룹핑
            service_resources = {}  # {service_prefix: {actions: [...], resources: [...]}}
            
            for policy in all_policies:
                statements = policy.get("Statement", [])
                
                for stmt in statements:
                    effect = stmt.get("Effect", "Allow")
                    if effect != "Allow":
                        continue
                    
                    actions = stmt.get("Action", [])
                    if not isinstance(actions, list):
                        actions = [actions]
                    
                    resources = stmt.get("Resource", [])
                    if not isinstance(resources, list):
                        resources = [resources]
                    
                    for action in actions:
                        # 서비스 프리픽스 추출 (예: "sqs:SendMessage" -> "sqs")
                        if action == "*":
                            service_prefix = "*"
                        else:
                            service_prefix = action.split(":")[0] if ":" in action else action
                        
                        if service_prefix not in service_resources:
                            service_resources[service_prefix] = {
                                "actions": [],
                                "resources": []
                            }
                        
                        if action not in service_resources[service_prefix]["actions"]:
                            service_resources[service_prefix]["actions"].append(action)
                        
                        # Resource 추가
                        for resource in resources:
                            if resource not in service_resources[service_prefix]["resources"]:
                                service_resources[service_prefix]["resources"].append(resource)
            
            # 실제 리소스와 매칭
            for service_prefix, info in service_resources.items():
                resources = info["resources"]
                actions = info["actions"]
                
                # Resource가 "*"인 경우 해당 서비스의 모든 리소스와 연결
                if "*" in resources:
                    for resource_node in node_list:
                        resource_type = str(resource_node.get("type")).lower()
                        resource_id = resource_node.get("id")
                        resource_name = resource_node.get("name")
                        
                        # Service와 리소스 타입 매칭
                        is_match = False
                        
                        if service_prefix == "sqs" and "sqs" in resource_type:
                            is_match = True
                        elif service_prefix == "rds" and "rds" in resource_type:
                            is_match = True
                        elif service_prefix == "ec2" and "ec2" in resource_type:
                            is_match = True
                        elif service_prefix == "lambda" and "lambda" in resource_type:
                            is_match = True
                        elif service_prefix == "logs" and "logs" in resource_type:
                            is_match = True
                        elif service_prefix == "*":
                            is_match = not resource_type.startswith("aws:")  # AWS 글로벌 서비스 제외
                        
                        if is_match:
                            edge_id = f"edge:{role_id}:ACCESSES_{service_prefix.upper()}:{resource_id}"
                            edges.append({
                                "id": edge_id,
                                "src": role_id,
                                "src_label": f"iam_role:{role_name}",
                                "dst": resource_id,
                                "dst_label": f"{resource_type}:{resource_name}",
                                "relation": f"ACCESSES_{service_prefix.upper()}",
                                "directed": True,
                                "conditions": [
                                    {
                                        "iam_role": {
                                            "attributes": {
                                                "policies": {
                                                    "inline_policies": inline_policies,
                                                    "attached_policies": attached_policies
                                                }
                                            },
                                            "service_actions": actions
                                        }
                                    }
                                ]
                            })
                            print(f"DEBUG: Role [{role_name}] can access [{resource_type}:{resource_name}]")
                else:
                    # 특정 ARN 리소스인 경우
                    for arn_resource in resources:
                        if arn_resource == "*":
                            continue
                        
                        # ARN에서 리소스 타입과 이름 추출
                        # 예: arn:aws:sqs:us-east-1:288528695623:cash_charging_queue
                        if ":" in arn_resource:
                            arn_parts = arn_resource.split(":")
                            res_service = arn_parts[2] if len(arn_parts) > 2 else ""
                            res_id_part = ":".join(arn_parts[5:]) if len(arn_parts) > 5 else ""
                            
                            # ARN 기반 리소스 찾기 (arn으로 매칭)
                            matching_resource = next(
                                (n for n in node_list if n.get("arn") == arn_resource),
                                None
                            )
                            
                            if matching_resource:
                                resource_id = matching_resource.get("id")
                                resource_type = matching_resource.get("type")
                                resource_name = matching_resource.get("name")
                                
                                edge_id = f"edge:{role_id}:ACCESSES_{service_prefix.upper()}:{resource_id}"
                                edges.append({
                                    "id": edge_id,
                                    "src": role_id,
                                    "src_label": f"iam_role:{role_name}",
                                    "dst": resource_id,
                                    "dst_label": f"{resource_type}:{resource_name}",
                                    "relation": f"ACCESSES_{service_prefix.upper()}",
                                    "directed": True,
                                    "conditions": [
                                        {
                                            "iam_role": {
                                                "attributes": {
                                                    "policies": {
                                                        "inline_policies": inline_policies,
                                                        "attached_policies": attached_policies
                                                    }
                                                },
                                                "service_actions": actions,
                                                "resource_arn": arn_resource
                                            }
                                        }
                                    ]
                                })
                                print(f"DEBUG: Role [{role_name}] can access specific resource [{resource_type}:{resource_name}]")
        
        print(f"--- [DEBUG] Role-Resource Linker Finished (generated {len(edges)} edges) ---\n")
        return edges