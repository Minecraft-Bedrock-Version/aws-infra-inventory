def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False

def extract_edges_for_vector(graph_data: dict) -> dict:

    vector_edges = []
    edges = graph_data.get("edges", [])

    for edge in edges:
        src = edge.get("src")
        dst = edge.get("dst")

        if not src or not dst:
            continue

        vector_edge = {
            "id": edge.get("id"), 
            "src": src,
            "dst": dst,
            "relation": edge.get("relation"), 
            "directed": to_bool(edge.get("directed")),
            "conditions": edge.get("conditions", [])
        }

        vector_edges.append(vector_edge)

    return {
        "edges": vector_edges
    }