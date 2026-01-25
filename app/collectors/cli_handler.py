from app.collectors.CliToNode import cli_put_user_policy_to_iam_user_json

def run_cli_collector(cli_input: str, account_id: str) -> dict:

    if not cli_input or cli_input.strip() == "":
        return {"nodes": [], "edges": []}
    
    try:
        cli_node_result = cli_put_user_policy_to_iam_user_json(
            cli_text=cli_input,
            account_id=account_id
        )
        return cli_node_result
        
    except Exception as e:
        print(f"CLI 변환 중 오류 발생: {e}")
        return {"nodes": [], "edges": []}