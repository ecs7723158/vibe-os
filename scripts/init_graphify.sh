#!/usr/bin/env bash
set -e

# ==============================================================================
# Upgraded Graphify Initialization & Knowledge Graph Generator
# ==============================================================================
# Scans Repo code (Python, Go, Frontend) + GOAL.md + TASKS.md using the official
# Graphify multi-language Tree-sitter AST engine & NetworkX graph clusterer.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/knowledge-graph"
GRAPHIFY_PYTHON="/Users/yi-fanshan/.gemini/antigravity-ide/scratch/graphify/.venv/bin/python"

echo "=================================================="
echo "   🚀 Graphify Engine: Local Knowledge Graph Generator"
echo "=================================================="
echo "Target Root: ${ROOT_DIR}"
echo "Output Dir:  ${OUTPUT_DIR}"

# Select appropriate python environment with graphify installed
if [ -x "${GRAPHIFY_PYTHON}" ]; then
    PY_BIN="${GRAPHIFY_PYTHON}"
elif command -v uv &>/dev/null && [ -f "${ROOT_DIR}/../graphify/pyproject.toml" ]; then
    PY_BIN="uv run --project ${ROOT_DIR}/../graphify python"
elif command -v python3 &>/dev/null; then
    PY_BIN="python3"
else
    echo "❌ Error: Python 3 with Graphify is required."
    exit 1
fi

echo "Using Python runtime: ${PY_BIN}"
mkdir -p "${OUTPUT_DIR}"

echo ""
echo "🔍 Scanning codebase, Tree-sitter AST, endpoints, and markdown specs..."
${PY_BIN} "${SCRIPT_DIR}/graphify_engine.py"

if [ -f "${OUTPUT_DIR}/knowledge_graph.json" ]; then
    NODE_COUNT=$(grep -c '"id":' "${OUTPUT_DIR}/knowledge_graph.json" || true)
    EDGE_COUNT=$(grep -c '"source":' "${OUTPUT_DIR}/knowledge_graph.json" || true)
    echo ""
    echo "=================================================="
    echo "   ✅ Upgraded Graphify Knowledge Graph Built Successfully!"
    echo "   - Extracted Nodes: ${NODE_COUNT}"
    echo "   - Extracted Edges: ${EDGE_COUNT}"
    echo "   - Artifacts:"
    echo "       * JSON:      ${OUTPUT_DIR}/knowledge_graph.json"
    echo "       * Mermaid:   ${OUTPUT_DIR}/knowledge_graph.mermaid"
    echo "       * DOT:       ${OUTPUT_DIR}/knowledge_graph.dot"
    [ -f "${OUTPUT_DIR}/graph.html" ] && echo "       * D3 HTML:   ${OUTPUT_DIR}/graph.html"
    [ -f "${OUTPUT_DIR}/GRAPH_REPORT.md" ] && echo "       * Report:    ${OUTPUT_DIR}/GRAPH_REPORT.md"
    [ -f "${OUTPUT_DIR}/callflow.html" ] && echo "       * Callflow:  ${OUTPUT_DIR}/callflow.html"
    echo "=================================================="
else
    echo "❌ Error: Knowledge graph generation failed."
    exit 1
fi
