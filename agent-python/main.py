import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI(
    title="Vibe OS - AI Agent Backend",
    description="Python FastAPI backend managing AI agent task execution and state machine",
    version="1.0.0"
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

def update_file_content(filepath: Path, content: str, append: bool = False):
    """Safely reads/writes content to control-state markdown files."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with open(filepath, mode, encoding="utf-8") as f:
        f.write(content)

async def mock_agent_execution_loop(task_id: str, description: str, agent_name: str):
    """Simulates a Vibe Coding agent execution loop with step-by-step progress logging."""
    
    # Step 0: Initialize
    broadcast_agent_status(agent_name, "STARTED", f"Received new task [{task_id}]: '{description}'. Initializing Vibe Coding session...")
    await asyncio.sleep(1.5)

    # Step 1: Read TASKS.md & state
    tasks_content = ""
    if TASKS_FILE.exists():
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            tasks_content = f.read()
    
    broadcast_agent_status(agent_name, "ANALYZING", f"Read TASKS.md. Analyzing task backlog and architecture context...")
    await asyncio.sleep(1.5)

    # Step 2: Code synthesis
    broadcast_agent_status(agent_name, "WRITING_CODE", f"Writing code modules & UI components for task [{task_id}]...")
    await asyncio.sleep(1.5)

    # Step 3: Testing & static analysis
    broadcast_agent_status(agent_name, "RUNNING_TESTS", f"Running automated unit test suite & static code verification...")
    await asyncio.sleep(1.5)

    # Step 4: Verification complete
    broadcast_agent_status(agent_name, "VERIFYING", f"Verification clean. Preparing agent handoff report for Waterfall Gate...")
    await asyncio.sleep(1.5)

    # Step 5: Waterfall Gate Trigger (WAITING_HUMAN_APPROVAL)
    status_msg = "Agent execution phase completed. Handoff package ready. Pausing at Waterfall Approval Gate."
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
  1. Analyzed backlog in `TASKS.md`.
  2. Generated Go WebSocket broadcast routes (`/ws/client`, `/api/agent-hook`).
  3. Integrated FastAPI agent state loop.
  4. Constructed Tailwind Cyberpunk UI frontend.
- **Next Action**: Awaiting Human Architect sign-off to proceed to deployment.
"""
    update_file_content(HANDOFF_FILE, handoff_entry, append=True)

@app.get("/")
def read_root():
    return {
        "system": "vibe-os",
        "service": "agent-python",
        "status": "running"
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

    # Update STATE.md immediately
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
    
    # Broadcast to Go server
    broadcast_agent_status("HumanArchitect", "APPROVED", f"Human Gate Approved by {req.reviewer}. Notes: {req.notes}")

    # Append to DECISIONS.md
    decision_entry = f"""

---

## Decision Record - {timestamp}
- **Reviewer**: {req.reviewer}
- **Decision**: {req.decision}
- **Notes**: {req.notes}
- **Status**: PASSED
"""
    update_file_content(DECISIONS_FILE, decision_entry, append=True)

    # Update STATE.md
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
