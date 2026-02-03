from typing import Dict, List, Set, Any

def extract_connected_subgraph(
    graph_nodes: List[Dict[str, Any]], 
    graph_edges: List[Dict[str, Any]],
    start_node_id: str,
) -> Dict[str, List]:

    node_index = {
        n.get("node_id"): n
        for n in graph_nodes
        if n.get("node_id")
    }
    adj = {n_id: [] for n_id in node_index}
    edge_map = {}
    
    if start_node_id not in node_index:
        return {"nodes": [], "edges": []}

    for edge in graph_edges:
        e_id = edge.get("id")
        src = edge.get("src")
        dst = edge.get("dst")
        
        if src in adj and dst in adj:
            adj[src].append((dst, e_id))
            adj[dst].append((src, e_id))
            edge_map[e_id] = edge

    visited_nodes: Set[str] = set()
    visited_edges: Set[str] = set()
    queue: List[str] = [start_node_id]

    while queue:
        current_node_id = queue.pop(0)

        if current_node_id in visited_nodes:
            continue

        visited_nodes.add(current_node_id)

        for neighbor_id, e_id in adj.get(current_node_id, []):
            visited_edges.add(e_id)
            if neighbor_id not in visited_nodes:
                queue.append(neighbor_id)

    return {
        "nodes": [node_index[nid] for nid in visited_nodes],
        "edges": [edge_map[eid] for eid in visited_edges],
    }