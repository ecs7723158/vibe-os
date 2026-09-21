# Vibe OS: Visualized Agile/Waterfall Hybrid Development System

`vibe-os` is a hybrid agentic architecture combining continuous agile velocity (log streaming, real-time agent execution) with waterfall governance gates (human sign-off before production changes).

---

## Directory Overview

```text
vibe-os/
├── frontend/
│   └── index.html          # Dark Mode Geek Control Center UI (Tailwind CSS + Vanilla JS WebSocket)
├── backend-go/             # High-concurrency WebSocket Gateway (Go 1.22+ / Gorilla WebSocket)
│   ├── main.go             # Handlers for /ws/client & /api/agent-hook
│   ├── go.mod
│   └── go.sum
├── agent-python/           # AI Agent Execution Layer & State Machine (FastAPI)
│   ├── main.py             # Task start loop, mock agent execution, Markdown state updates
│   └── requirements.txt
└── control-state/          # Markdown Source of Truth
    ├── GOAL.md             # Core system objectives
    ├── STATE.md            # System real-time state phase
    ├── TASKS.md            # Agile backlog tasks
    ├── HANDOFF.md          # AI Agent handoff summaries
    └── DECISIONS.md        # Human waterfall approval records
```

---

## Quick Start Guide

### Step 1: Start the Go WebSocket Gateway (`backend-go`)

1. Open a terminal and navigate to `backend-go`:
   ```bash
   cd backend-go
   ```
2. Run the Go WebSocket Gateway:
   ```bash
   go run main.go
   ```
   - **WebSocket Endpoint**: `ws://localhost:8080/ws/client`
   - **Agent Hook Endpoint**: `http://localhost:8080/api/agent-hook`

---

### Step 2: Start the Python Agent Backend (`agent-python`)

1. Open a second terminal window and navigate to `agent-python`:
   ```bash
   cd agent-python
   ```
2. (Optional) Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   - **Service Endpoint**: `http://localhost:8000`
   - **Interactive API Documentation**: `http://localhost:8000/docs`

---

### Step 3: Launch the Frontend Control Dashboard (`frontend`)

1. Open `frontend/index.html` in your web browser (or serve it using standard static web server):
   ```bash
   open frontend/index.html
   ```
   or using python HTTP server:
   ```bash
   python3 -m http.server 3000 --directory frontend
   ```
2. Check the top bar connection indicator:
   - **WS: Connected** (Green dot indicates successful WebSocket link to port 8080).

---

## Interactive Workflow Verification

1. **Trigger Task**:
   - In the **Control Operations** panel (Right side), enter a Task ID and Description.
   - Click **START AGENT (POST :8000)**.
2. **Observe Real-Time Stream**:
   - Watch the **Vibe Terminal** (Center panel) append real-time log entries streamed from the Python Agent through the Go Gateway every 1.5s.
   - Observe the **System State Board** (Left panel) transition to `AGILE_RUNNING`.
3. **Waterfall Approval Gate**:
   - When the agent finishes processing, it emits `WAITING_HUMAN_APPROVAL` status and records a handover package into `control-state/HANDOFF.md`.
   - The Waterfall Gate lamp will illuminate yellow (`GATE_LOCKED`).
4. **Human Sign-Off**:
   - Click **APPROVE WATERFALL GATE** on the Control Panel.
   - The Python server appends decision notes to `control-state/DECISIONS.md` and updates `control-state/STATE.md` to `APPROVED` phase.

---

## Security & Environment Integrity

- **API Keys**: No API keys or credentials are hardcoded.
- **Port Mapping**:
  - `8080`: Go WebSocket Gateway
  - `8000`: Python FastAPI Agent Service
