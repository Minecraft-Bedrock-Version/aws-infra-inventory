from app.filters.filter import extract_connected_subgraph

def run_filters(full_graph: dict, start_node_id: str) -> dict:

    nodes = full_graph.get("nodes", [])
    edges = full_graph.get("edges", [])

    if not start_node_id:
        return {"nodes": [], "edges": []}
    
    result = extract_connected_subgraph(
        graph_nodes=nodes,
        graph_edges=edges,
        start_node_id=start_node_id
    )
    
    return result