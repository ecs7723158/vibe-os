#!/usr/bin/env bash
set -e

# ==============================================================================
# Graphify Initialization & Knowledge Graph Generator
# ==============================================================================
# Scans Repo code (Python, Go, Frontend) + GOAL.md + TASKS.md to build
# local knowledge graph topology for AI Agent workflow.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/knowledge-graph"

echo "=================================================="
echo "   🚀 Graphify Engine: Local Knowledge Graph Generator"
echo "=================================================="
echo "Target Root: ${ROOT_DIR}"
echo "Output Dir:  ${OUTPUT_DIR}"

if ! command -v python3 &>/dev/null; then
    echo "❌ Error: python3 is required to run Graphify engine."
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"

echo ""
echo "🔍 Scanning codebase, AST trees, endpoints, and markdown specs..."
python3 "${SCRIPT_DIR}/graphify_engine.py"

if [ -f "${OUTPUT_DIR}/knowledge_graph.json" ]; then
    NODE_COUNT=$(grep -c '"id":' "${OUTPUT_DIR}/knowledge_graph.json" || true)
    EDGE_COUNT=$(grep -c '"source":' "${OUTPUT_DIR}/knowledge_graph.json" || true)
    echo ""
    echo "=================================================="
    echo "   ✅ Graphify Knowledge Graph Built Successfully!"
    echo "   - Extracted Nodes: ${NODE_COUNT}"
    echo "   - Extracted Edges: ${EDGE_COUNT}"
    echo "   - Artifacts:"
    echo "       * JSON:    ${OUTPUT_DIR}/knowledge_graph.json"
    echo "       * DOT:     ${OUTPUT_DIR}/knowledge_graph.dot"
    echo "       * Mermaid: ${OUTPUT_DIR}/knowledge_graph.mermaid"
    echo "=================================================="
else
    echo "❌ Error: Knowledge graph generation failed."
    exit 1
fi
