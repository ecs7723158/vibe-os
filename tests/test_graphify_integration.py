"""
Test Suite for Graphify Integration & MCP Code Graph Querying in Vibe OS
"""

import json
import os
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "agent-python"))
sys.path.append(str(BASE_DIR / "scripts"))

from graph_service import query_code_graph, ensure_graph_exists


class TestGraphifyIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure graph is generated
        ensure_graph_exists()

    def test_knowledge_graph_json_structure(self):
        """Verify knowledge_graph.json exists and contains correct schema."""
        graph_file = BASE_DIR / "knowledge-graph" / "knowledge_graph.json"
        self.assertTrue(graph_file.exists(), "knowledge_graph.json must exist")

        with open(graph_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("version"), "1.0.0")
        self.assertIn("summary", data)
        self.assertGreater(data["summary"]["nodes_count"], 15)
        self.assertGreater(data["summary"]["edges_count"], 10)

        # Check essential nodes
        node_ids = {n["id"] for n in data.get("nodes", [])}
        self.assertIn("goal:system", node_ids)
        self.assertIn("service:agent-python", node_ids)
        self.assertIn("service:backend-go", node_ids)
        self.assertIn("service:frontend", node_ids)

    def test_dot_and_mermaid_artifacts(self):
        """Verify DOT and Mermaid diagrams are generated."""
        dot_file = BASE_DIR / "knowledge-graph" / "knowledge_graph.dot"
        mermaid_file = BASE_DIR / "knowledge-graph" / "knowledge_graph.mermaid"

        self.assertTrue(dot_file.exists(), "knowledge_graph.dot must exist")
        self.assertTrue(mermaid_file.exists(), "knowledge_graph.mermaid must exist")

        dot_content = dot_file.read_text(encoding="utf-8")
        self.assertTrue(dot_content.startswith("digraph"))

        mermaid_content = mermaid_file.read_text(encoding="utf-8")
        self.assertTrue(mermaid_content.startswith("graph TD"))

    def test_query_code_graph_overview(self):
        """Verify overview query returns complete topology."""
        res = query_code_graph("overview")
        self.assertEqual(res.get("status"), "success")
        self.assertGreater(res.get("total_nodes", 0), 20)
        self.assertGreater(res.get("total_edges", 0), 15)
        self.assertIn("Service: Python Agent (FastAPI)", res.get("services", []))
        self.assertIn("Service: Go WebSocket Gateway", res.get("services", []))

    def test_query_code_graph_dependencies(self):
        """Verify dependency query on main.py returns connections."""
        res = query_code_graph("dependencies", target="main.py")
        self.assertEqual(res.get("status"), "success")
        self.assertIn("outgoing_dependencies", res)
        self.assertIn("incoming_dependents", res)
        self.assertGreaterEqual(len(res["outgoing_dependencies"]), 1)

    def test_query_code_graph_impact_analysis(self):
        """Verify blast radius impact analysis computes risk level."""
        res = query_code_graph("impact_analysis", target="main.py")
        self.assertEqual(res.get("status"), "success")
        self.assertIn(res.get("blast_radius_risk"), ["LOW", "MEDIUM", "HIGH"])
        self.assertGreater(res.get("impacted_nodes_count", 0), 3)
        self.assertIn("recommendation", res)

    def test_query_code_graph_task_mapping(self):
        """Verify task mapping can find code nodes related to tasks."""
        res = query_code_graph("task_mapping", target="TASK-001")
        self.assertEqual(res.get("status"), "success")
        self.assertIn("implementing_components", res)


if __name__ == "__main__":
    unittest.main()
