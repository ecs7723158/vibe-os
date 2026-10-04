#!/usr/bin/env python3
"""
Graphify Engine for Vibe OS
===========================
Scans repository source code (Python AST, Go, Frontend JS/HTML) and Markdown specifications
(GOAL.md, TASKS.md) to generate a comprehensive, structured knowledge graph.

Outputs:
  - knowledge-graph/knowledge_graph.json
  - knowledge-graph/knowledge_graph.dot
  - knowledge-graph/knowledge_graph.mermaid
"""

import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any


class GraphifyEngine:
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

    def add_edge(self, source: str, target: str, relation: str, metadata: Dict[str, Any] = None):
        edge = {
            "source": source,
            "target": target,
            "relation": relation,
            "metadata": metadata or {}
        }
        if edge not in self.edges:
            self.edges.append(edge)

    def scan_markdown_specifications(self):
        """Scans GOAL.md, TASKS.md, STATE.md for system architecture intent."""
        control_dir = self.root_dir / "control-state"
        if not control_dir.exists():
            return

        # 1. Parse GOAL.md
        goal_file = control_dir / "GOAL.md"
        if goal_file.exists():
            content = goal_file.read_text(encoding="utf-8")
            self.add_node("goal:system", "System Goal (Vibe OS)", "goal", {"path": str(goal_file.relative_to(self.root_dir))})
            
            # Extract capabilities / core objectives
            capabilities = re.findall(r"\d+\.\s+\*\*([^*]+)\*\*:\s*([^\n]+)", content)
            for name, desc in capabilities:
                node_id = f"capability:{name.strip().lower().replace(' ', '_')}"
                self.add_node(node_id, f"Capability: {name.strip()}", "capability", {"description": desc.strip()})
                self.add_edge("goal:system", node_id, "fulfills")

        # 2. Parse TASKS.md (supports both Markdown tables and checkbox lists)
        tasks_file = control_dir / "TASKS.md"
        if tasks_file.exists():
            content = tasks_file.read_text(encoding="utf-8")
            
            # Pattern A: Table rows | TASK-001 | Description | Priority | Status |
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

            # Pattern B: Checkbox lists - [x] TASK-001: Description
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

    def scan_python_agent(self):
        """Uses AST to parse Python Agent codebase (FastAPI routes, functions, cross-calls)."""
        py_dir = self.root_dir / "agent-python"
        if not py_dir.exists():
            return

        service_node = "service:agent-python"
        self.add_node(service_node, "Service: Python Agent (FastAPI)", "service", {"tech": "Python / FastAPI"})

        for py_path in py_dir.rglob("*.py"):
            if "venv" in py_path.parts or "__pycache__" in py_path.parts:
                continue
            
            rel_path = str(py_path.relative_to(self.root_dir))
            file_node = f"file:{rel_path}"
            self.add_node(file_node, py_path.name, "file", {"language": "python", "path": rel_path})
            self.add_edge(service_node, file_node, "contains")

            try:
                content = py_path.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(py_path))

                for node in ast.walk(tree):
                    # Inspect functions
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        fn_node = f"py_func:{py_path.stem}.{node.name}"
                        self.add_node(fn_node, f"def {node.name}()", "function", {"file": rel_path, "lineno": node.lineno})
                        self.add_edge(file_node, fn_node, "declares")

                        # Check for FastAPI route decorators
                        for dec in node.decorator_list:
                            dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else ""
                            if any(verb in dec_str for verb in [".get", ".post", ".put", ".delete", ".websocket"]):
                                route_match = re.search(r"app\.(get|post|put|delete|websocket)\([\"']([^\"']+)[\"']", dec_str)
                                if route_match:
                                    method, path = route_match.groups()
                                    ep_node = f"endpoint:python:{method.upper()}_{path}"
                                    self.add_node(ep_node, f"{method.upper()} {path}", "endpoint", {"service": "agent-python", "path": path, "method": method.upper()})
                                    self.add_edge(fn_node, ep_node, "routes_to")

                    # Inspect calls to Go Gateway (e.g. requests.post)
                    if isinstance(node, ast.Call):
                        call_str = ast.unparse(node) if hasattr(ast, "unparse") else ""
                        if "GO_GATEWAY_URL" in call_str or "agent-hook" in call_str:
                            self.add_edge(file_node, "endpoint:go:POST_/api/agent-hook", "calls", {"protocol": "HTTP/REST"})

            except Exception as e:
                print(f"[Warning] AST parse failed for {rel_path}: {e}")

    def scan_go_backend(self):
        """Scans Go WebSocket Gateway codebase for routes, hubs, and handlers."""
        go_dir = self.root_dir / "backend-go"
        if not go_dir.exists():
            return

        service_node = "service:backend-go"
        self.add_node(service_node, "Service: Go WebSocket Gateway", "service", {"tech": "Go / Gorilla WebSocket"})

        # Predefine known Go endpoints
        hook_ep = "endpoint:go:POST_/api/agent-hook"
        self.add_node(hook_ep, "POST /api/agent-hook", "endpoint", {"service": "backend-go", "path": "/api/agent-hook", "method": "POST"})
        self.add_edge(service_node, hook_ep, "exposes")

        ws_ep = "endpoint:go:WS_/ws/client"
        self.add_node(ws_ep, "WS /ws/client", "endpoint", {"service": "backend-go", "path": "/ws/client", "method": "WEBSOCKET"})
        self.add_edge(service_node, ws_ep, "exposes")

        health_ep = "endpoint:go:GET_/health"
        self.add_node(health_ep, "GET /health", "endpoint", {"service": "backend-go", "path": "/health", "method": "GET"})
        self.add_edge(service_node, health_ep, "exposes")

        # Hub broadcasts to WebSocket clients
        self.add_edge(hook_ep, ws_ep, "broadcasts_to", {"channel": "hub.broadcast"})

        for go_path in go_dir.rglob("*.go"):
            rel_path = str(go_path.relative_to(self.root_dir))
            file_node = f"file:{rel_path}"
            self.add_node(file_node, go_path.name, "file", {"language": "go", "path": rel_path})
            self.add_edge(service_node, file_node, "contains")

            content = go_path.read_text(encoding="utf-8")
            # Extract struct types
            structs = re.findall(r"type\s+([A-Za-z0-9_]+)\s+struct", content)
            for s in structs:
                s_node = f"go_struct:{s}"
                self.add_node(s_node, f"type {s} struct", "struct", {"file": rel_path})
                self.add_edge(file_node, s_node, "declares")

            # Extract func declarations
            funcs = re.findall(r"func\s+(?:\([^)]+\)\s+)?([A-Za-z0-9_]+)\s*\(", content)
            for f in funcs:
                f_node = f"go_func:{f}"
                self.add_node(f_node, f"func {f}()", "function", {"file": rel_path})
                self.add_edge(file_node, f_node, "declares")

    def scan_frontend(self):
        """Scans Frontend codebase for WebSocket subscriptions and API calls."""
        fe_dir = self.root_dir / "frontend"
        if not fe_dir.exists():
            return

        ui_node = "service:frontend"
        self.add_node(ui_node, "Frontend Dashboard", "service", {"tech": "HTML5 / Tailwind CSS / Vanilla JS"})

        for html_path in fe_dir.rglob("*.html"):
            rel_path = str(html_path.relative_to(self.root_dir))
            file_node = f"file:{rel_path}"
            self.add_node(file_node, html_path.name, "file", {"language": "html", "path": rel_path})
            self.add_edge(ui_node, file_node, "contains")

            content = html_path.read_text(encoding="utf-8")
            # Detect WebSocket client connection
            if "/ws/client" in content:
                self.add_edge(file_node, "endpoint:go:WS_/ws/client", "subscribes_to", {"protocol": "WebSocket"})

            # Detect fetch calls to Python agent
            if "/v1/state" in content:
                self.add_edge(file_node, "endpoint:python:GET_/v1/state", "calls", {"protocol": "HTTP/REST"})
            if "/v1/task/start" in content:
                self.add_edge(file_node, "endpoint:python:POST_/v1/task/start", "calls", {"protocol": "HTTP/REST"})

    def link_tasks_to_code(self):
        """Connects high-level tasks to the code components that implement them."""
        # Map TASK-001 (WebSocket Gateway)
        if "task:TASK-001" in self.nodes and "service:backend-go" in self.nodes:
            self.add_edge("task:TASK-001", "service:backend-go", "implemented_by")
        
        # Map TASK-002 (FastAPI Agent)
        if "task:TASK-002" in self.nodes and "service:agent-python" in self.nodes:
            self.add_edge("task:TASK-002", "service:agent-python", "implemented_by")

        # Map TASK-003 (Frontend Dashboard)
        if "task:TASK-003" in self.nodes and "service:frontend" in self.nodes:
            self.add_edge("task:TASK-003", "service:frontend", "implemented_by")

    def export(self):
        """Exports the graph in JSON, DOT, and Mermaid formats."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 1. JSON Export
        graph_data = {
            "version": "1.0.0",
            "generator": "Graphify-vibe-os",
            "summary": {
                "nodes_count": len(self.nodes),
                "edges_count": len(self.edges),
                "services": [n["label"] for n in self.nodes.values() if n["type"] == "service"]
            },
            "nodes": list(self.nodes.values()),
            "edges": self.edges
        }
        json_path = self.output_dir / "knowledge_graph.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)

        # 2. DOT (Graphviz) Export
        dot_path = self.output_dir / "knowledge_graph.dot"
        with open(dot_path, "w", encoding="utf-8") as f:
            f.write("digraph VibeOSKnowledgeGraph {\n")
            f.write('  rankdir=LR;\n  node [shape=box, fontname="Helvetica"];\n  edge [fontname="Helvetica", fontsize=10];\n\n')
            for n in self.nodes.values():
                safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", n["id"])
                f.write(f'  {safe_id} [label="{n["label"]}", type="{n["type"]}"];\n')
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

        print(f"[Graphify] Generated Knowledge Graph successfully:")
        print(f"  - Nodes: {len(self.nodes)}")
        print(f"  - Edges: {len(self.edges)}")
        print(f"  - JSON:    {json_path}")
        print(f"  - DOT:     {dot_path}")
        print(f"  - Mermaid: {mermaid_path}")


def main():
    root = Path(__file__).resolve().parent.parent
    out = root / "knowledge-graph"
    engine = GraphifyEngine(root_dir=root, output_dir=out)
    engine.scan_markdown_specifications()
    engine.scan_python_agent()
    engine.scan_go_backend()
    engine.scan_frontend()
    engine.link_tasks_to_code()
    engine.export()


if __name__ == "__main__":
    main()
