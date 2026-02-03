"""
IAM CLI 파서

IAM 관련 AWS CLI 명령어를 파싱하여 노드/엣지로 변환합니다.
"""

import json
import re
from typing import Dict, Any, List
from .base_parser import BaseParser


class IAMParser(BaseParser):
    """IAM CLI 명령어 파서 - 9가지 명령어 지원"""
    
    @property
    def service_name(self) -> str:
        return "iam"
    
    @property
    def supported_commands(self) -> List[str]:
        return [
            "create-user",
            "put-user-policy",
            "attach-user-policy",
            "create-role",
            "put-role-policy",
            "attach-role-policy",
            "create-group",
            "put-group-policy",
            "add-user-to-group"
        ]
    
    def parse_command(self, cli_text: str, account_id: str, **kwargs) -> Dict[str, Any]:
        """
        IAM CLI 명령어 파싱
        
        자동으로 명령어 타입을 감지하고 적절한 파서로 위임
        """
        cli_normalized = self._collapse_cli(cli_text).lower()
        
        # 명령어 타입 감지 및 파싱
        if "create-user" in cli_normalized:
            return self._parse_create_user(cli_text, account_id)
        elif "put-user-policy" in cli_normalized:
            return self._parse_put_user_policy(cli_text, account_id)
        elif "attach-user-policy" in cli_normalized:
            return self._parse_attach_user_policy(cli_text, account_id)
        elif "create-role" in cli_normalized:
            return self._parse_create_role(cli_text, account_id)
        elif "put-role-policy" in cli_normalized:
            return self._parse_put_role_policy(cli_text, account_id)
        elif "attach-role-policy" in cli_normalized:
            return self._parse_attach_role_policy(cli_text, account_id)
        elif "create-group" in cli_normalized:
            return self._parse_create_group(cli_text, account_id)
        elif "put-group-policy" in cli_normalized:
            return self._parse_put_group_policy(cli_text, account_id)
        elif "add-user-to-group" in cli_normalized:
            return self._parse_add_user_to_group(cli_text, account_id)
        else:
            raise ValueError(f"Unsupported IAM command: {cli_text[:100]}...")
    
    # ===== User Commands =====
    
    def _parse_create_user(self, cli_text: str, account_id: str) -> Dict:
        """Parse: aws iam create-user --user-name X"""
        cli_one = self._collapse_cli(cli_text)
        user_name = self._extract_flag_value(cli_one, "--user-name")
        
        if not user_name:
            raise ValueError("--user-name required for create-user")
        
        node_id = f"{account_id}:iam_user:{user_name}"
        
        return {
            "schema_version": "1.0",
            "collected_at": self._iso_now(),
            "account_id": account_id,
            "nodes": [{
                "node_type": "iam_user",
                "node_id": node_id,
                "resource_id": user_name,
                "name": user_name,
                "attributes": {
                    "arn": f"arn:aws:iam::{account_id}:user/{user_name}",
                    "create_date": self._iso_now(),
                    "attached_policies": [],
                    "inline_policies": [],
                    "group_policies": []
                },
                "raw_refs": {
                    "source": ["cli:aws iam create-user"],
                    "collected_at": self._iso_now()
                }
            }],
            "edges": []
        }
    
    def _parse_put_user_policy(self, cli_text: str, account_id: str) -> Dict:
        """Parse: aws iam put-user-policy --user-name X --policy-name Y --policy-document '{...}'"""
        cli_one = self._collapse_cli(cli_text)
        
        user_name = self._extract_flag_value(cli_one, "--user-name")
        policy_name = self._extract_flag_value(cli_one, "--policy-name")
        
        if not user_name or not policy_name:
            raise ValueError("--user-name and --policy-name required")
        
        # Extract policy document
        policy_doc_raw = self._extract_policy_document(cli_text)
        policy_doc = json.loads(policy_doc_raw)
        
        statements = policy_doc.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]
        
        inline_policy = {
            "PolicyName": policy_name,
            "PolicyDocument": {"Statement": [self._normalize_statement(s) for s in statements if isinstance(s, dict)]}
        }
        
        node_id = f"{account_id}:iam_user:{user_name}"
        
        return {
            "schema_version": "1.0",
            "collected_at": self._iso_now(),
            "account_id": account_id,
            "nodes": [{
                "node_type": "iam_user",
                "node_id": node_id,
                "resource_id": user_name,
                "name": user_name,
                "attributes": {
                    "arn": f"arn:aws:iam::{account_id}:user/{user_name}",
                    "create_date": self._iso_now(),
                    "attached_policies": [],
                    "inline_policies": [inline_policy],
                    "group_policies": []
                },
                "raw_refs": {
                    "source": ["cli:aws iam put-user-policy"],
                    "collected_at": self._iso_now()
                }
            }],
            "edges": []
        }
    
    def _parse_attach_user_policy(self, cli_text: str, account_id: str) -> Dict:
        """Parse: aws iam attach-user-policy --user-name X --policy-arn Y"""
        cli_one = self._collapse_cli(cli_text)
        
        user_name = self._extract_flag_value(cli_one, "--user-name")
        policy_arn = self._extract_flag_value(cli_one, "--policy-arn")
        
        if not user_name or not policy_arn:
            raise ValueError("--user-name and --policy-arn required")
        
        policy_name = policy_arn.split("/")[-1] if "/" in policy_arn else policy_arn
        
        node_id = f"iam_user:{account_id}:{user_name}"
        
        return {
            "schema_version": "1.0",
            "collected_at": self._iso_now(),
            "account_id": account_id,
            "nodes": [{
                "node_type": "iam_user",
                "node_id": node_id,
                "resource_id": user_name,
                "name": user_name,
                "attributes": {
                    "arn": f"arn:aws:iam::{account_id}:user/{user_name}",
                    "create_date": self._iso_now(),
                    "attached_policies": [{
                        "PolicyName": policy_name,
                        "PolicyArn": policy_arn
                    }],
                    "inline_policies": [],
                    "group_policies": []
                },
                "raw_refs": {
                    "source": ["cli:aws iam attach-user-policy"],
                    "collected_at": self._iso_now()
                }
            }],
            "edges": []
        }
    
    # ===== Role Commands =====
    
    def _parse_create_role(self, cli_text: str, account_id: str) -> Dict:
        """Parse: aws iam create-role --role-name X --assume-role-policy-document '{...}'"""
        cli_one = self._collapse_cli(cli_text)
        
        role_name = self._extract_flag_value(cli_one, "--role-name")
        if not role_name:
            raise ValueError("--role-name required")
        
        # Trust policy (assume role policy)
        trust_policy_raw = self._extract_policy_document(cli_text, "--assume-role-policy-document")
        trust_policy = json.loads(trust_policy_raw)
        
        node_id = f"iam_role:{account_id}:{role_name}"
        
        return {
            "schema_version": "1.0",
            "collected_at": self._iso_now(),
            "account_id": account_id,
            "nodes": [{
                "node_type": "iam_role",
                "node_id": node_id,
                "resource_id": role_name,
                "name": role_name,
                "attributes": {
                    "arn": f"arn:aws:iam::{account_id}:role/{role_name}",
                    "create_date": self._iso_now(),
                    "assume_role_policy": trust_policy,
                    "attached_policies": [],
                    "inline_policies": []
                },
                "raw_refs": {
                    "source": ["cli:aws iam create-role"],
                    "collected_at": self._iso_now()
                }
            }],
            "edges": []
        }
    
    def _parse_put_role_policy(self, cli_text: str, account_id: str) -> Dict:
        """Parse: aws iam put-role-policy --role-name X --policy-name Y --policy-document '{...}'"""
        cli_one = self._collapse_cli(cli_text)
        
        role_name = self._extract_flag_value(cli_one, "--role-name")
        policy_name = self._extract_flag_value(cli_one, "--policy-name")
        
        if not role_name or not policy_name:
            raise ValueError("--role-name and --policy-name required")
        
        # Extract policy document
        policy_doc_raw = self._extract_policy_document(cli_text)
        policy_doc = json.loads(policy_doc_raw)
        
        statements = policy_doc.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]
        
        inline_policy = {
            "PolicyName": policy_name,
            "Statement": [self._normalize_statement(s) for s in statements if isinstance(s, dict)]
        }
        
        node_id = f"iam_role:{account_id}:{role_name}"
        
        return {
            "schema_version": "1.0",
            "collected_at": self._iso_now(),
            "account_id": account_id,
            "nodes": [{
                "node_type": "iam_role",
                "node_id": node_id,
                "resource_id": role_name,
                "name": role_name,
                "attributes": {
                    "arn": f"arn:aws:iam::{account_id}:role/{role_name}",
                    "create_date": self._iso_now(),
                    "assume_role_policy": {},  # Not provided in this command
                    "attached_policies": [],
                    "inline_policies": [inline_policy]
                },
                "raw_refs": {
                    "source": ["cli:aws iam put-role-policy"],
                    "collected_at": self._iso_now()
                }
            }],
            "edges": []
        }
    
    def _parse_attach_role_policy(self, cli_text: str, account_id: str) -> Dict:
        """Parse: aws iam attach-role-policy --role-name X --policy-arn Y"""
        cli_one = self._collapse_cli(cli_text)
        
        role_name = self._extract_flag_value(cli_one, "--role-name")
        policy_arn = self._extract_flag_value(cli_one, "--policy-arn")
        
        if not role_name or not policy_arn:
            raise ValueError("--role-name and --policy-arn required")
        
        policy_name = policy_arn.split("/")[-1] if "/" in policy_arn else policy_arn
        
        node_id = f"iam_role:{account_id}:{role_name}"
        
        return {
            "schema_version": "1.0",
            "collected_at": self._iso_now(),
            "account_id": account_id,
            "nodes": [{
                "node_type": "iam_role",
                "node_id": node_id,
                "resource_id": role_name,
                "name": role_name,
                "attributes": {
                    "arn": f"arn:aws:iam::{account_id}:role/{role_name}",
                    "create_date": self._iso_now(),
                    "assume_role_policy": {},
                    "attached_policies": [{
                        "PolicyName": policy_name,
                        "PolicyArn": policy_arn
                    }],
                    "inline_policies": []
                },
                "raw_refs": {
                    "source": ["cli:aws iam attach-role-policy"],
                    "collected_at": self._iso_now()
                }
            }],
            "edges": []
        }
    
    # ===== Group Commands =====
    
    def _parse_create_group(self, cli_text: str, account_id: str) -> Dict:
        """Parse: aws iam create-group --group-name X"""
        cli_one = self._collapse_cli(cli_text)
        group_name = self._extract_flag_value(cli_one, "--group-name")
        
        if not group_name:
            raise ValueError("--group-name required")
        
        node_id = f"iam_group:{account_id}:{group_name}"
        
        return {
            "schema_version": "1.0",
            "collected_at": self._iso_now(),
            "account_id": account_id,
            "nodes": [{
                "node_type": "iam_group",
                "node_id": node_id,
                "resource_id": group_name,
                "name": group_name,
                "attributes": {
                    "arn": f"arn:aws:iam::{account_id}:group/{group_name}",
                    "create_date": self._iso_now(),
                    "attached_policies": [],
                    "inline_policies": []
                },
                "raw_refs": {
                    "source": ["cli:aws iam create-group"],
                    "collected_at": self._iso_now()
                }
            }],
            "edges": []
        }
    
    def _parse_put_group_policy(self, cli_text: str, account_id: str) -> Dict:
        """Parse: aws iam put-group-policy --group-name X --policy-name Y --policy-document '{...}'"""
        cli_one = self._collapse_cli(cli_text)
        
        group_name = self._extract_flag_value(cli_one, "--group-name")
        policy_name = self._extract_flag_value(cli_one, "--policy-name")
        
        if not group_name or not policy_name:
            raise ValueError("--group-name and --policy-name required")
        
        # Extract policy document
        policy_doc_raw = self._extract_policy_document(cli_text)
        policy_doc = json.loads(policy_doc_raw)
        
        statements = policy_doc.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]
        
        inline_policy = {
            "PolicyName": policy_name,
            "Statement": [self._normalize_statement(s) for s in statements if isinstance(s, dict)]
        }
        
        node_id = f"iam_group:{account_id}:{group_name}"
        
        return {
            "schema_version": "1.0",
            "collected_at": self._iso_now(),
            "account_id": account_id,
            "nodes": [{
                "node_type": "iam_group",
                "node_id": node_id,
                "resource_id": group_name,
                "name": group_name,
                "attributes": {
                    "arn": f"arn:aws:iam::{account_id}:group/{group_name}",
                    "create_date": self._iso_now(),
                    "attached_policies": [],
                    "inline_policies": [inline_policy]
                },
                "raw_refs": {
                    "source": ["cli:aws iam put-group-policy"],
                    "collected_at": self._iso_now()
                }
            }],
            "edges": []
        }
    
    def _parse_add_user_to_group(self, cli_text: str, account_id: str) -> Dict:
        """Parse: aws iam add-user-to-group --user-name X --group-name Y"""
        cli_one = self._collapse_cli(cli_text)
        
        user_name = self._extract_flag_value(cli_one, "--user-name")
        group_name = self._extract_flag_value(cli_one, "--group-name")
        
        if not user_name or not group_name:
            raise ValueError("--user-name and --group-name required")
        
        # This command creates an edge relationship, but we'll represent it as updating the user node
        user_node_id = f"iam_user:{account_id}:{user_name}"
        
        return {
            "schema_version": "1.0",
            "collected_at": self._iso_now(),
            "account_id": account_id,
            "nodes": [{
                "node_type": "iam_user",
                "node_id": user_node_id,
                "resource_id": user_name,
                "name": user_name,
                "attributes": {
                    "arn": f"arn:aws:iam::{account_id}:user/{user_name}",
                    "create_date": self._iso_now(),
                    "attached_policies": [],
                    "inline_policies": [],
                    "group_policies": [],
                    "groups": [group_name]  # User belongs to this group
                },
                "raw_refs": {
                    "source": ["cli:aws iam add-user-to-group"],
                    "collected_at": self._iso_now()
                }
            }],
            "edges": []  # Edge creation is handled by filtering/graph assembly
        }
    
    # ===== Helper Methods =====
    
    def _extract_policy_document(self, cli_text: str, flag: str = "--policy-document") -> str:
        """
        Extract policy JSON from CLI command
        
        Args:
            cli_text: CLI command text
            flag: Flag name (default: --policy-document)
            
        Returns:
            str: JSON string of policy document
        """
        s = self._collapse_cli(cli_text)
        
        # Try single quotes
        m = re.search(rf"{re.escape(flag)}\s+'(.+?)'\s*(?:--|$)", s)
        if m:
            return m.group(1).strip()
        
        # Try double quotes
        m = re.search(rf'{re.escape(flag)}\s+"(.+?)"\s*(?:--|$)', s)
        if m:
            return m.group(1).strip()
        
        # No quotes (rare)
        m = re.search(rf"{re.escape(flag)}\s+(\\{{.+\\}})\\s*(?:--|$)", s)
        if m:
            return m.group(1).strip()
        
        raise ValueError(f"Could not extract {flag} from CLI")
    
    @staticmethod
    def _normalize_statement(stmt: Dict) -> Dict:
        """
        Normalize policy statement to standard format
        
        Args:
            stmt: Policy statement dictionary
            
        Returns:
            Normalized statement
        """
        effect = stmt.get("Effect")
        
        # Normalize Action to list
        action = stmt.get("Action")
        if isinstance(action, list):
            action_list = action
        elif isinstance(action, str):
            action_list = [action]
        else:
            action_list = []
        
        # Normalize Resource to string
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