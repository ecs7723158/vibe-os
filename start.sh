#!/bin/bash

# Vibe OS Startup Script
# Usage: ./start.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=================================================="
echo " Starting Vibe OS Visualized Hybrid Dev Platform"
echo " Root: $PROJECT_ROOT"
echo "=================================================="

# Function to kill child processes on exit
cleanup() {
    echo ""
    echo "[Vibe OS] Shutting down services..."
    if [ -f "$PROJECT_ROOT/vibe-os.pid" ]; then
        kill $(cat "$PROJECT_ROOT/vibe-os.pid") 2>/dev/null || true
        rm -f "$PROJECT_ROOT/vibe-os.pid"
    fi
    echo "[Vibe OS] All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 1. Start Go WebSocket Gateway (Port 8080)
echo "[1/3] Launching Go WebSocket Gateway on :8080..."
cd "$PROJECT_ROOT/backend-go"
go run main.go > "$PROJECT_ROOT/backend-go.log" 2>&1 &
GO_PID=$!
echo $GO_PID >> "$PROJECT_ROOT/vibe-os.pid"

# 2. Start Python Agent Backend (Port 8000)
echo "[2/3] Launching Python FastAPI Agent Backend on :8000..."
cd "$PROJECT_ROOT/agent-python"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt > /dev/null 2>&1
fi
./venv/bin/uvicorn main:app --port 8000 --reload > "$PROJECT_ROOT/agent-python.log" 2>&1 &
PY_PID=$!
echo $PY_PID >> "$PROJECT_ROOT/vibe-os.pid"

# 3. Start Frontend HTTP Server (Port 3000)
echo "[3/3] Launching Frontend Web Server on :3000..."
cd "$PROJECT_ROOT/frontend"
python3 -m http.server 3000 > "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID >> "$PROJECT_ROOT/vibe-os.pid"

sleep 2

echo "=================================================="
echo " Vibe OS is running successfully!"
echo " - Go Gateway:      ws://localhost:8080/ws/client"
echo " - Python Backend:  http://localhost:8000"
echo " - Frontend Web:    http://localhost:3000"
echo " Press Ctrl+C to stop all services."
echo "=================================================="

# Wait for background processes
wait
