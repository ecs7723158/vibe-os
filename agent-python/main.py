import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests

from graph_service import query_code_graph

app = FastAPI(
    title="Vibe OS - AI Agent Backend & Graphify Engine",
    description="Python FastAPI backend managing AI agent task execution, Graphify knowledge graph queries, and state machine",
    version="1.1.0"
)

# Enable CORS for frontend interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths to control state files
BASE_DIR = Path(__file__).resolve().parent
CONTROL_STATE_DIR = BASE_DIR.parent / "control-state"
GOAL_FILE = CONTROL_STATE_DIR / "GOAL.md"
STATE_FILE = CONTROL_STATE_DIR / "STATE.md"
TASKS_FILE = CONTROL_STATE_DIR / "TASKS.md"
HANDOFF_FILE = CONTROL_STATE_DIR / "HANDOFF.md"
DECISIONS_FILE = CONTROL_STATE_DIR / "DECISIONS.md"

GO_GATEWAY_URL = "http://localhost:8080/api/agent-hook"


class TaskStartRequest(BaseModel):
    task_id: Optional[str] = "TASK-001"
    description: Optional[str] = "Build Vibe OS visual dashboard & state broadcast system"
    agent_name: Optional[str] = "VibeAgent-01"


class ApprovalRequest(BaseModel):
    reviewer: Optional[str] = "Human Lead Architect"
    decision: Optional[str] = "APPROVED"
    notes: Optional[str] = "Waterfall gate passed. Code release authorized."


class GraphQueryRequest(BaseModel):
    query_type: str = Field("dependencies", description="One of: 'dependencies', 'impact_analysis', 'task_mapping', 'overview'")
    target: Optional[str] = Field(None, description="Target node, file, or task id")


class AgentTraceRequest(BaseModel):
    agent_name: Optional[str] = "VibeAgent-01"
    stage: str = "THINKING"
    thought_log: str
    graph_context: Optional[Dict[str, Any]] = None


class MCPCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


def broadcast_agent_status(agent_name: str, status: str, log_message: str):
    """Sends log payloads to Go WebSocket gateway for real-time frontend streaming."""
    payload = {
        "agent_name": agent_name,
        "status": status,
        "log_message": log_message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    try:
        response = requests.post(GO_GATEWAY_URL, json=payload, timeout=2.0)
        print(f"[Agent -> Go Gateway] {status}: {log_message} (HTTP {response.status_code})")
    except Exception as e:
        print(f"[Agent -> Go Gateway Warning] Failed to reach Go gateway on {GO_GATEWAY_URL}: {e}")


def broadcast_agent_trace(agent_name: str, stage: str, thought_log: str, graph_context: Optional[Dict[str, Any]] = None):
    """Broadcasts detailed agent thinking path and knowledge graph reasoning to Go WebSocket server."""
    trace_msg = f"[{stage}] {thought_log}"
    broadcast_agent_status(agent_name, "AGENT_TRACE", trace_msg)


def update_file_content(filepath: Path, content: str, append: bool = False):
    """Safely reads/writes content to control-state markdown files."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with open(filepath, mode, encoding="utf-8") as f:
        f.write(content)


async def mock_agent_execution_loop(task_id: str, description: str, agent_name: str):
    """
    Vibe Coding agent execution loop integrated with Graphify Knowledge Graph.
    Queries dependencies and evaluates architectural blast radius before synthesizing changes.
    """
    # Step 0: Initialize
    broadcast_agent_status(agent_name, "STARTED", f"Received new task [{task_id}]: '{description}'. Initializing Vibe Coding session...")
    await asyncio.sleep(1.0)

    # Step 1: Read TASKS.md & specifications
    broadcast_agent_status(agent_name, "ANALYZING", f"Read TASKS.md and GOAL.md. Preparing architectural context...")
    await asyncio.sleep(1.0)

    # Step 1.5: Graphify Knowledge Graph Query & Thinking Trace
    broadcast_agent_trace(
        agent_name,
        "GRAPH_QUERY",
        f"Querying Graphify Knowledge Graph to inspect architectural blast radius for task [{task_id}]..."
    )
    await asyncio.sleep(1.0)

    # Execute graph impact analysis
    graph_impact = query_code_graph(query_type="impact_analysis", target="main.py")
    risk = graph_impact.get("blast_radius_risk", "LOW")
    impacted_count = graph_impact.get("impacted_nodes_count", 0)
    services = graph_impact.get("affected_services", [])

    trace_thought = (
        f"Graphify Dependency Analysis: Target 'agent-python/main.py' connects to {impacted_count} nodes "
        f"across services {services}. Blast Radius Risk: {risk}. "
        f"Architectural Rule: Ensuring backward-compatibility for Go WebSocket '/api/agent-hook' protocol."
    )
    broadcast_agent_trace(agent_name, "GRAPH_TRACE", trace_thought, graph_context=graph_impact)
    await asyncio.sleep(1.2)

    # Step 2: Code synthesis
    broadcast_agent_status(agent_name, "WRITING_CODE", f"Graphify constraints verified. Writing code modules & UI components for task [{task_id}]...")
    await asyncio.sleep(1.2)

    # Step 3: Testing & static analysis
    broadcast_agent_status(agent_name, "RUNNING_TESTS", f"Running automated unit test suite & static code verification...")
    await asyncio.sleep(1.2)

    # Step 4: Verification complete
    broadcast_agent_status(agent_name, "VERIFYING", f"Verification clean. Preparing agent handoff report for Waterfall Gate...")
    await asyncio.sleep(1.0)

    # Step 5: Waterfall Gate Trigger (WAITING_HUMAN_APPROVAL)
    status_msg = "Agent execution phase completed. Graphify constraints verified. Pausing at Waterfall Approval Gate."
    broadcast_agent_status(agent_name, "WAITING_HUMAN_APPROVAL", status_msg)

    # Update STATE.md
    state_update = f"""# Current System State

- **Current Phase**: WAITING_HUMAN_APPROVAL
- **Agent Status**: PAUSED (Waterfall Gate Locked)
- **Active Task**: {task_id} - {description}
- **Waterfall Gate**: PENDING_APPROVAL
- **Last Updated**: {datetime.utcnow().isoformat()}Z
"""
    update_file_content(STATE_FILE, state_update, append=False)

    # Update HANDOFF.md
    handoff_entry = f"""

---

## Handoff Record - {datetime.utcnow().isoformat()}Z
- **Task ID**: {task_id}
- **Task Description**: {description}
- **Agent Name**: {agent_name}
- **Status**: WAITING_HUMAN_APPROVAL
- **Execution Summary**:
  1. Analyzed backlog in `TASKS.md` & `GOAL.md`.
  2. Queried Graphify knowledge graph (Blast Radius Risk: {risk}, Nodes: {impacted_count}).
  3. Verified cross-service API schema compatibility with Go WebSocket Gateway.
  4. Executed automated verification suite cleanly.
- **Next Action**: Awaiting Human Architect sign-off to proceed to deployment.
"""
    update_file_content(HANDOFF_FILE, handoff_entry, append=True)


@app.get("/")
def read_root():
    return {
        "system": "vibe-os",
        "service": "agent-python",
        "status": "running",
        "graphify_enabled": True
    }


@app.get("/v1/state")
def get_current_state():
    """Returns the current state from control-state files."""
    state_text = STATE_FILE.read_text(encoding="utf-8") if STATE_FILE.exists() else "No STATE.md found"
    tasks_text = TASKS_FILE.read_text(encoding="utf-8") if TASKS_FILE.exists() else "No TASKS.md found"
    handoff_text = HANDOFF_FILE.read_text(encoding="utf-8") if HANDOFF_FILE.exists() else "No HANDOFF.md found"
    decisions_text = DECISIONS_FILE.read_text(encoding="utf-8") if DECISIONS_FILE.exists() else "No DECISIONS.md found"

    return {
        "state": state_text,
        "tasks": tasks_text,
        "handoff": handoff_text,
        "decisions": decisions_text
    }


@app.post("/v1/task/start")
def start_task(req: TaskStartRequest, background_tasks: BackgroundTasks):
    """Endpoint to launch a new Vibe Coding agent task execution loop."""
    background_tasks.add_task(
        mock_agent_execution_loop,
        task_id=req.task_id,
        description=req.description,
        agent_name=req.agent_name
    )

    state_update = f"""# Current System State

- **Current Phase**: AGILE_RUNNING
- **Agent Status**: BUSY ({req.agent_name})
- **Active Task**: {req.task_id} - {req.description}
- **Waterfall Gate**: LOCKED
- **Last Updated**: {datetime.utcnow().isoformat()}Z
"""
    update_file_content(STATE_FILE, state_update, append=False)

    return {
        "status": "accepted",
        "message": f"Task {req.task_id} started successfully",
        "task_id": req.task_id
    }


@app.post("/v1/task/approve")
def approve_waterfall_gate(req: ApprovalRequest):
    """Endpoint for human sign-off approving the waterfall gate."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    broadcast_agent_status("HumanArchitect", "APPROVED", f"Human Gate Approved by {req.reviewer}. Notes: {req.notes}")

    decision_entry = f"""

---

## Decision Record - {timestamp}
- **Reviewer**: {req.reviewer}
- **Decision**: {req.decision}
- **Notes**: {req.notes}
- **Status**: PASSED
"""
    update_file_content(DECISIONS_FILE, decision_entry, append=True)

    state_update = f"""# Current System State

- **Current Phase**: APPROVED
- **Agent Status**: IDLE (Gate Unlocked)
- **Active Task**: None
- **Waterfall Gate**: PASSED
- **Last Updated**: {timestamp}
"""
    update_file_content(STATE_FILE, state_update, append=False)

    return {
        "status": "success",
        "message": "Waterfall Gate approved successfully",
        "timestamp": timestamp
    }


# ==============================================================================
# Graphify Knowledge Graph & MCP Endpoints
# ==============================================================================

@app.post("/v1/graph/query")
def graph_query(req: GraphQueryRequest):
    """REST endpoint for querying Graphify code knowledge graph."""
    res = query_code_graph(query_type=req.query_type, target=req.target)
    return res


@app.post("/v1/agent/trace")
def forward_agent_trace(req: AgentTraceRequest):
    """Forwards an agent's reasoning/thinking trace directly to the Go WebSocket Server."""
    broadcast_agent_trace(
        agent_name=req.agent_name or "VibeAgent-01",
        stage=req.stage,
        thought_log=req.thought_log,
        graph_context=req.graph_context
    )
    return {"status": "broadcasted"}


@app.get("/v1/mcp/tools")
def get_mcp_tools():
    """Returns standard MCP tool definitions available in Vibe OS."""
    return {
        "tools": [
            {
                "name": "query_code_graph",
                "description": "Queries the Graphify knowledge graph to inspect code dependencies, architecture impact, and task-to-code mappings before modifying files.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": ["dependencies", "impact_analysis", "task_mapping", "overview"],
                            "description": "Type of query to perform against the knowledge graph."
                        },
                        "target": {
                            "type": "string",
                            "description": "Target node id, file path, function name, or task ID to analyze."
                        }
                    },
                    "required": ["query_type"]
                }
            }
        ]
    }


@app.post("/v1/mcp/tools/call")
def call_mcp_tool(req: MCPCallRequest):
    """Executes an MCP tool call (query_code_graph) and returns standardized content."""
    if req.name == "query_code_graph":
        q_type = req.arguments.get("query_type", "dependencies")
        target = req.arguments.get("target")
        result = query_code_graph(query_type=q_type, target=target)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2, ensure_ascii=False)
                }
            ],
            "isError": result.get("status") == "error"
        }
    raise HTTPException(status_code=404, detail=f"Tool '{req.name}' not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
