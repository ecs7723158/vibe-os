"""
Graph Service for Vibe OS Agent
===============================
Provides local Knowledge Graph querying and architectural impact analysis for AI Agents
prior to code synthesis and modifications.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
GRAPH_DIR = ROOT_DIR / "knowledge-graph"
GRAPH_JSON_FILE = GRAPH_DIR / "knowledge_graph.json"
GRAPH_ENGINE_SCRIPT = ROOT_DIR / "scripts" / "graphify_engine.py"


def ensure_graph_exists() -> Dict[str, Any]:
    """Loads knowledge_graph.json, generating it via graphify_engine.py if missing."""
    if not GRAPH_JSON_FILE.exists():
        if GRAPH_ENGINE_SCRIPT.exists():
            subprocess.run(["python3", str(GRAPH_ENGINE_SCRIPT)], cwd=str(ROOT_DIR), check=True)
        else:
            return {"nodes": [], "edges": [], "summary": {}}
    
    try:
        with open(GRAPH_JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[GraphService Error] Failed to read knowledge graph: {e}")
        return {"nodes": [], "edges": [], "summary": {}}


def find_matching_nodes(graph: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """Fuzzy searches nodes by id or label."""
    if not query:
        return []
    q = query.strip().lower()
    matches = []
    for n in graph.get("nodes", []):
        if q in n["id"].lower() or q in n["label"].lower():
            matches.append(n)
    return matches


def query_code_graph(query_type: str = "dependencies", target: Optional[str] = None) -> Dict[str, Any]:
    """
    Queries Graphify knowledge graph to inspect code dependencies, architecture impact,
    and task-to-code mappings before modifying files.

    Args:
        query_type: One of ['dependencies', 'impact_analysis', 'task_mapping', 'overview']
        target: Target node id, file path, function name, or task ID
    """
    graph = ensure_graph_exists()
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    if query_type == "overview":
        services = [n for n in nodes if n.get("type") == "service"]
        endpoints = [n for n in nodes if n.get("type") == "endpoint"]
        tasks = [n for n in nodes if n.get("type") == "task"]
        return {
            "status": "success",
            "query_type": "overview",
            "summary": graph.get("summary", {}),
            "services": [s["label"] for s in services],
            "endpoints": [e["label"] for e in endpoints],
            "tasks_count": len(tasks),
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }

    if not target:
        return {
            "status": "error",
            "message": f"Target must be specified for query_type '{query_type}'"
        }

    matched_nodes = find_matching_nodes(graph, target)
    if not matched_nodes:
        return {
            "status": "not_found",
            "query_type": query_type,
            "target": target,
            "message": f"No node in knowledge graph matches target: '{target}'"
        }

    primary_node = matched_nodes[0]
    node_id = primary_node["id"]

    if query_type == "dependencies":
        outgoing = [e for e in edges if e["source"] == node_id]
        incoming = [e for e in edges if e["target"] == node_id]
        return {
            "status": "success",
            "query_type": "dependencies",
            "target": primary_node,
            "outgoing_dependencies": outgoing,
            "incoming_dependents": incoming,
            "dependency_summary": f"Node '{primary_node['label']}' calls/depends on {len(outgoing)} components and is depended on by {len(incoming)} components."
        }

    elif query_type == "impact_analysis":
        # BFS Traversal for upstream and downstream impacts (depth 2)
        impacted_node_ids = {node_id}
        visited_edges = []
        
        queue = [node_id]
        depth_map = {node_id: 0}

        while queue:
            curr = queue.pop(0)
            curr_depth = depth_map[curr]
            if curr_depth >= 2:
                continue

            for e in edges:
                # Downstream impact (things that depend on this or called by this)
                other = None
                if e["source"] == curr:
                    other = e["target"]
                elif e["target"] == curr:
                    other = e["source"]

                if other and other not in impacted_node_ids:
                    impacted_node_ids.add(other)
                    depth_map[other] = curr_depth + 1
                    visited_edges.append(e)
                    queue.append(other)

        impacted_nodes_info = [n for n in nodes if n["id"] in impacted_node_ids]
        affected_services = list({n["metadata"].get("service") or n["label"] for n in impacted_nodes_info if n.get("type") in ("service", "endpoint")})

        # Calculate architectural blast radius risk
        risk = "LOW"
        if len(affected_services) > 1 or any(n.get("type") == "endpoint" for n in impacted_nodes_info):
            risk = "HIGH"
        elif len(impacted_nodes_info) > 3:
            risk = "MEDIUM"

        return {
            "status": "success",
            "query_type": "impact_analysis",
            "target": primary_node,
            "blast_radius_risk": risk,
            "impacted_nodes_count": len(impacted_nodes_info),
            "impacted_nodes": impacted_nodes_info,
            "affected_services": affected_services,
            "recommendation": f"Risk level {risk}. Modify with care. Ensure contracts with {affected_services} remain backwards compatible."
        }

    elif query_type == "task_mapping":
        related_edges = [e for e in edges if e["source"] == node_id or e["target"] == node_id]
        related_node_ids = {e["source"] for e in related_edges} | {e["target"] for e in related_edges}
        related_nodes = [n for n in nodes if n["id"] in related_node_ids and n["id"] != node_id]
        return {
            "status": "success",
            "query_type": "task_mapping",
            "task": primary_node,
            "implementing_components": related_nodes,
            "edges": related_edges
        }

    return {
        "status": "error",
        "message": f"Unknown query_type: '{query_type}'"
    }
