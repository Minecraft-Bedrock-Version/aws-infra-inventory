from datetime import datetime, timezone
from typing import List, Dict, Any

from graph_builder.iam_user_graph import transform_iam_users
from graph_builder.iam_role_graph import transform_iam_roles
from graph_builder.igw_graph import transform_igw_to_graph
from graph_builder.ec2_graph import transform_ec2_to_graph
from graph_builder.rds_graph import transform_rds_to_graph
from graph_builder.route_table_graph import transform_route_table_to_graph
from graph_builder.subnet_graph import transform_subnet_to_graph
from graph_builder.vpc_graph import transform_to_graph_format transform_vpc


class GraphAssembler:
	    def assemble(self, resource_graphs: List[Dict[str, Any]]) -> Dict[str, Any]:
        master_nodes: Dict[str, Dict[str, Any]] = {}
        master_edges: Dict[str, Dict[str, Any]] = {}

        account_id = None
        collected_at_list = []
					
        for graph in resource_graphs:
						
            if not account_id and graph.get("account_id"):
                account_id = graph.get("account_id")

            if graph.get("collected_at"):
                collected_at_list.append(graph["collected_at"])

            for node in graph.get("nodes", []):
                node_id = node.get("id")

                if not node_id:
                    continue  

                if node_id not in master_nodes:
                    master_nodes[node_id] = node
                else:
                    existing_node = master_nodes[node_id]
                    merged_node = self._merge_nodes(existing_node, node)
                    master_nodes[node_id] = merged_node

						# 노드 병합	
            for edge in graph.get("edges", []):
                edge_id = edge.get("id")

                if not edge_id:
                    continue  

                if edge_id not in master_edges:
                    master_edges[edge_id] = edge
                else:
                    existing_edge = master_edges[edge_id]
                    merged_edge = self._merge_edges(existing_edge, edge)
                    master_edges[edge_id] = merged_edge

        if collected_at_list:
            final_collected_at = max(collected_at_list)
        else:
            final_collected_at = datetime.now(timezone.utc).isoformat()

        output_graph = {
            "schema_version": "1.0",        
            "collected_at": final_collected_at,
            "account_id": account_id,
            "nodes": list(master_nodes.values()),
            "edges": list(master_edges.values())
        }

        return output_graph

    def _merge_nodes(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:

        merged = dict(old)

        for key in ["type", "name", "arn", "region"]:
            if not merged.get(key) and new.get(key):
                merged[key] = new[key]

        old_props = old.get("properties", {})
        new_props = new.get("properties", {})

        merged_props = dict(old_props)

        for prop_key, prop_value in new_props.items():
            if prop_key not in merged_props:
                merged_props[prop_key] = prop_value
            else:
                merged_props[prop_key] = self._merge_property_value(
                    merged_props[prop_key],
                    prop_value
                )

        merged["properties"] = merged_props

        return merged

    def _merge_property_value(self, old_value: Any, new_value: Any) -> Any:

        if isinstance(old_value, dict) and isinstance(new_value, dict):
            merged = dict(old_value)
            for k, v in new_value.items():
                if k not in merged:
                    merged[k] = v
                else:
                    merged[k] = self._merge_property_value(merged[k], v)
            return merged

        if isinstance(old_value, list) and isinstance(new_value, list):
            return list({*old_value, *new_value})
            
        return new_value

    def _merge_edges(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:

        merged = dict(old)

        for key in ["relation", "src", "dst", "src_label", "dst_label", "directed"]:
            if not merged.get(key) and new.get(key):
                merged[key] = new[key]

        old_conditions = old.get("conditions", [])
        new_conditions = new.get("conditions", [])

        if old_conditions or new_conditions:
            merged_conditions = []

            seen = set()
            for cond in old_conditions + new_conditions:
                key = f"{cond.get('key')}={cond.get('value')}"
                if key not in seen:
                    seen.add(key)
                    merged_conditions.append(cond)

            merged["conditions"] = merged_conditions

        return merged
