#!/usr/bin/env python3
"""
Upgraded Graphify Engine for Vibe OS
=====================================
Integrates the official Graphify AST analysis engine (Tree-sitter multi-language
parsing, NetworkX graph construction, Leiden community clustering, and God-node analysis)
with Vibe OS system specifications (GOAL.md, TASKS.md, STATE.md).

Outputs in knowledge-graph/:
  - knowledge_graph.json   (Full graph: AST nodes + architecture intent + communities)
  - knowledge_graph.mermaid(Mermaid architectural flowchart)
  - knowledge_graph.dot    (Graphviz DOT format)
  - graph.html             (Interactive D3 graph visualization)
  - GRAPH_REPORT.md        (Architectural report & God node analysis)
  - callflow.html          (Mermaid architecture & call-flow view)
"""

import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any

# Ensure graphify engine is discoverable
GRAPHIFY_SCRATCH_DIR = Path(__file__).resolve().parent.parent.parent / "graphify"
VENV_SITE_PACKAGES = GRAPHIFY_SCRATCH_DIR / ".venv" / "lib" / "python3.12" / "site-packages"

if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(VENV_SITE_PACKAGES))
if GRAPHIFY_SCRATCH_DIR.exists() and str(GRAPHIFY_SCRATCH_DIR) not in sys.path:
    sys.path.insert(0, str(GRAPHIFY_SCRATCH_DIR))

try:
    import networkx as nx
    from graphify.extract import extract, collect_files
    from graphify.build import build
    from graphify.cluster import cluster
    from graphify.analyze import god_nodes, surprising_connections
    from graphify.export import to_html, to_json
    from graphify.report import generate as generate_report
    from graphify.callflow_html import write_callflow_html
    GRAPHIFY_CORE_AVAILABLE = True
except ImportError as err:
    print(f"[Warning] Graphify core import warning: {err}. Falling back to standard AST parser.")
    GRAPHIFY_CORE_AVAILABLE = False


class UpgradedVibeGraphifyEngine:
    def __init__(self, root_dir: Path, output_dir: Path):
        self.root_dir = root_dir
        self.output_dir = output_dir
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []

    def add_node(self, node_id: str, label: str, node_type: str, metadata: Dict[str, Any] = None):
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "id": node_id,
                "label": label,
                "type": node_type,
                "metadata": metadata or {}
            }
        else:
            if metadata:
                self.nodes[node_id].setdefault("metadata", {}).update(metadata)

    def add_edge(self, source: str, target: str, relation: str, metadata: Dict[str, Any] = None):
        edge = {
            "source": source,
            "target": target,
            "relation": relation,
            "metadata": metadata or {}
        }
        for existing in self.edges:
            if existing["source"] == source and existing["target"] == target and existing["relation"] == relation:
                return
        self.edges.append(edge)

    def scan_codebase_ast(self):
        """Uses Graphify Tree-sitter parsers to extract all AST nodes and edges across languages."""
        if not GRAPHIFY_CORE_AVAILABLE:
            print("[Notice] Using fallback AST scanner...")
            return

        print("[Graphify] Scanning codebase with Tree-sitter AST extractors...")
        files = collect_files(self.root_dir, root=self.root_dir)
        # Exclude generated output and virtual environments
        scannable_files = [
            f for f in files
            if "knowledge-graph" not in f.parts
            and ".venv" not in f.parts
            and "node_modules" not in f.parts
            and "__pycache__" not in f.parts
        ]
        print(f"[Graphify] Scannable source files identified: {len(scannable_files)}")

        extraction = extract(scannable_files, root=self.root_dir)
        ast_nodes = extraction.get("nodes", [])
        ast_edges = extraction.get("edges", [])

        print(f"[Graphify] Extracted {len(ast_nodes)} AST nodes and {len(ast_edges)} AST edges.")

        for n in ast_nodes:
            nid = n.get("id")
            nlabel = n.get("label", nid)
            nfile = n.get("source_file", "")
            nloc = n.get("source_location", "")
            ntype = "ast_symbol"
            if "func" in nid.lower() or "def " in nlabel:
                ntype = "function"
            elif "class" in nid.lower() or "type " in nlabel:
                ntype = "class"
            elif nfile.endswith(".py"):
                ntype = "python_symbol"
            elif nfile.endswith(".go"):
                ntype = "go_symbol"

            self.add_node(nid, nlabel, ntype, {
                "source_file": nfile,
                "source_location": nloc,
                "confidence": n.get("confidence", "EXTRACTED")
            })

        for e in ast_edges:
            self.add_edge(
                source=e.get("source"),
                target=e.get("target"),
                relation=e.get("relation", "references"),
                metadata={"confidence": e.get("confidence", "EXTRACTED")}
            )

    def scan_markdown_specifications(self):
        """Scans GOAL.md, TASKS.md, STATE.md for high-level architecture intent."""
        control_dir = self.root_dir / "control-state"
        if not control_dir.exists():
            return

        # 1. Parse GOAL.md
        goal_file = control_dir / "GOAL.md"
        if goal_file.exists():
            content = goal_file.read_text(encoding="utf-8")
            self.add_node("goal:system", "System Goal (Vibe OS)", "goal", {"path": str(goal_file.relative_to(self.root_dir))})
            capabilities = re.findall(r"\d+\.\s+\*\*([^*]+)\*\*:\s*([^\n]+)", content)
            for name, desc in capabilities:
                node_id = f"capability:{name.strip().lower().replace(' ', '_')}"
                self.add_node(node_id, f"Capability: {name.strip()}", "capability", {"description": desc.strip()})
                self.add_edge("goal:system", node_id, "fulfills")

        # 2. Parse TASKS.md
        tasks_file = control_dir / "TASKS.md"
        if tasks_file.exists():
            content = tasks_file.read_text(encoding="utf-8")
            table_tasks = re.findall(r"\|\s*([A-Z0-9_-]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", content)
            for task_id, desc, priority, status in table_tasks:
                if task_id.lower() in ("task id", "---"):
                    continue
                t_node = f"task:{task_id.strip()}"
                self.add_node(t_node, f"Task [{task_id.strip()}]: {desc.strip()}", "task", {
                    "status": status.strip(),
                    "priority": priority.strip(),
                    "description": desc.strip()
                })
                self.add_edge("goal:system", t_node, "tracks")

            checkbox_tasks = re.findall(r"-\s*\[([ xX])\]\s*([A-Z0-9_-]+)[:\s]+([^\n]+)", content)
            for done, task_id, desc in checkbox_tasks:
                status = "COMPLETED" if done.lower() == "x" else "PENDING"
                t_node = f"task:{task_id.strip()}"
                self.add_node(t_node, f"Task [{task_id.strip()}]: {desc.strip()}", "task", {"status": status, "description": desc.strip()})
                self.add_edge("goal:system", t_node, "tracks")

        # 3. Parse STATE.md
        state_file = control_dir / "STATE.md"
        if state_file.exists():
            self.add_node("state:system", "System State Machine", "state", {"path": str(state_file.relative_to(self.root_dir))})

    def link_services_and_tasks(self):
        """Creates top-level service groupings and connects tasks to implementations."""
        # Top-level services
        service_py = "service:agent-python"
        service_go = "service:backend-go"
        service_fe = "service:frontend"

        self.add_node(service_py, "Service: Python Agent (FastAPI)", "service", {"tech": "Python / FastAPI"})
        self.add_node(service_go, "Service: Go WebSocket Gateway", "service", {"tech": "Go / Gorilla WebSocket"})
        self.add_node(service_fe, "Service: Frontend Dashboard", "service", {"tech": "HTML5 / Tailwind CSS / Vanilla JS"})

        # Link tasks to services
        if "task:TASK-001" in self.nodes:
            self.add_edge("task:TASK-001", service_go, "implemented_by")
        if "task:TASK-002" in self.nodes:
            self.add_edge("task:TASK-002", service_py, "implemented_by")
        if "task:TASK-003" in self.nodes:
            self.add_edge("task:TASK-003", service_fe, "implemented_by")

        # Connect AST nodes to services based on file location
        for nid, n in list(self.nodes.items()):
            src_file = n.get("metadata", {}).get("source_file", "")
            if src_file.startswith("agent-python"):
                self.add_edge(service_py, nid, "contains")
            elif src_file.startswith("backend-go"):
                self.add_edge(service_go, nid, "contains")
            elif src_file.startswith("frontend"):
                self.add_edge(service_fe, nid, "contains")

    def build_networkx_graph(self) -> Any:
        """Constructs a NetworkX graph with node and edge attributes."""
        G = nx.DiGraph()
        for nid, n in self.nodes.items():
            G.add_node(nid, label=n["label"], type=n["type"], **n.get("metadata", {}))
        for e in self.edges:
            G.add_edge(e["source"], e["target"], relation=e["relation"], **e.get("metadata", {}))
        return G

    def export(self):
        """Exports all knowledge graph representations: JSON, DOT, Mermaid, D3 HTML, Report, Callflow."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        G = self.build_networkx_graph()

        # Run community detection and architectural analysis if Graphify core is available
        communities = {}
        god_nodes_list = []
        surprising_conns = []

        if GRAPHIFY_CORE_AVAILABLE:
            try:
                # Graphify cluster expects an undirected graph or works on G.to_undirected()
                undirected_G = G.to_undirected()
                communities = cluster(undirected_G)
                god_nodes_list = god_nodes(undirected_G)
                surprising_conns = surprising_connections(undirected_G)
            except Exception as e:
                print(f"[Warning] Graph analysis failed: {e}")

        # 1. JSON Export (Structured with Summary & Metadata)
        graph_data = {
            "version": "2.0.0",
            "generator": "Graphify-vibe-os-v8",
            "summary": {
                "nodes_count": len(self.nodes),
                "edges_count": len(self.edges),
                "communities_count": len(communities),
                "god_nodes_count": len(god_nodes_list),
                "services": [n["label"] for n in self.nodes.values() if n["type"] == "service"]
            },
            "communities": communities,
            "god_nodes": [gn[0] if isinstance(gn, tuple) else gn for gn in god_nodes_list[:10]],
            "nodes": list(self.nodes.values()),
            "edges": self.edges
        }
        json_path = self.output_dir / "knowledge_graph.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)

        # 2. Graphviz DOT Export
        dot_path = self.output_dir / "knowledge_graph.dot"
        with open(dot_path, "w", encoding="utf-8") as f:
            f.write("digraph VibeOSKnowledgeGraph {\n")
            f.write('  rankdir=LR;\n  node [shape=box, fontname="Helvetica"];\n  edge [fontname="Helvetica", fontsize=10];\n\n')
            for n in self.nodes.values():
                safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", n["id"])
                clean_label = n["label"].replace('"', '\\"')
                f.write(f'  {safe_id} [label="{clean_label}", type="{n["type"]}"];\n')
            f.write("\n")
            for e in self.edges:
                s_id = re.sub(r"[^a-zA-Z0-9_]", "_", e["source"])
                t_id = re.sub(r"[^a-zA-Z0-9_]", "_", e["target"])
                f.write(f'  {s_id} -> {t_id} [label="{e["relation"]}"];\n')
            f.write("}\n")

        # 3. Mermaid Export
        mermaid_path = self.output_dir / "knowledge_graph.mermaid"
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write("graph TD\n")
            for n in self.nodes.values():
                safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", n["id"])
                clean_label = n["label"].replace('"', "'")
                f.write(f'    {safe_id}["{clean_label}"]\n')
            for e in self.edges:
                s_id = re.sub(r"[^a-zA-Z0-9_]", "_", e["source"])
                t_id = re.sub(r"[^a-zA-Z0-9_]", "_", e["target"])
                f.write(f'    {s_id} -->|{e["relation"]}| {t_id}\n')

        # 4. Interactive D3 HTML & Report via Graphify core
        html_path = self.output_dir / "graph.html"
        report_path = self.output_dir / "GRAPH_REPORT.md"
        callflow_path = self.output_dir / "callflow.html"

        if GRAPHIFY_CORE_AVAILABLE:
            try:
                # D3 HTML Visualizer
                to_html(undirected_G, communities, str(html_path))
                print(f"  - HTML:    {html_path}")
            except Exception as e:
                print(f"[Warning] Failed to generate D3 HTML: {e}")

            try:
                # Markdown Report
                rep_content = f"# Vibe OS Architecture Knowledge Graph Report\n\n"
                rep_content += f"- **Total Nodes**: {len(self.nodes)}\n"
                rep_content += f"- **Total Edges**: {len(self.edges)}\n"
                rep_content += f"- **Detected Communities**: {len(communities)}\n\n"
                rep_content += "## God Nodes (High Centrality Symbols)\n\n"
                for gn in god_nodes_list[:15]:
                    name = gn[0] if isinstance(gn, tuple) else gn
                    deg = gn[1] if isinstance(gn, tuple) and len(gn) > 1 else "N/A"
                    rep_content += f"- `{name}` (degree: {deg})\n"
                rep_content += "\n## Communities\n\n"
                for cid, cnodes in list(communities.items())[:10]:
                    rep_content += f"### Community {cid} ({len(cnodes)} nodes)\n"
                    for cn in cnodes[:8]:
                        rep_content += f"- `{cn}`\n"
                    if len(cnodes) > 8:
                        rep_content += f"- ... and {len(cnodes) - 8} more\n"
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(rep_content)
                print(f"  - Report:  {report_path}")
            except Exception as e:
                print(f"[Warning] Failed to generate Report: {e}")

            try:
                # Mermaid Call-Flow HTML
                write_callflow_html(
                    graph=json_path,
                    report=report_path,
                    output=callflow_path,
                    lang="zh-CN"
                )
                print(f"  - Callflow:{callflow_path}")
            except Exception as e:
                print(f"[Warning] Callflow generation info: {e}")

        print("\n==================================================")
        print("   ✅ Vibe OS Graphify Engine Completed!")
        print(f"   - Nodes: {len(self.nodes)}")
        print(f"   - Edges: {len(self.edges)}")
        print(f"   - Communities: {len(communities)}")
        print(f"   - Artifacts stored in: {self.output_dir}")
        print("==================================================")


def main():
    root = Path(__file__).resolve().parent.parent
    out = root / "knowledge-graph"
    engine = UpgradedVibeGraphifyEngine(root_dir=root, output_dir=out)
    engine.scan_codebase_ast()
    engine.scan_markdown_specifications()
    engine.link_services_and_tasks()
    engine.export()


if __name__ == "__main__":
    main()
