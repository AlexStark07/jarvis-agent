# JARVIS Personal AI Operating System

JARVIS is a multi-agent AI operating system built around LangGraph, FastAPI, and Docker-isolated execution workers. It features 5 specialist agents managed by a parent supervisor, robust SQLite transaction handling, and a React-based frontend dashboard.

## Features

- **Supervisor Orchestration:** Delegates tasks intelligently to 5 specialist agents.
- **Isolated Execution:** Sandboxes all code execution inside unprivileged Docker containers to protect the host.
- **Durable Task Processing:** Handles long-running multi-agent workflows across process restarts using atomic SQLite leases.
- **Human Approvals:** Requires manual approval for infrastructure deployment, message transmission, and host-desktop actions.
- **Voice Capabilities:** Includes voice endpoints connected to Whisper/TTS models for natural interaction.

## Local Setup (Windows / PowerShell via Antigravity IDE)

### 1. Prerequisites
- Python 3.11+
- Node.js (for the frontend dashboard)
- Docker Desktop (Required for isolated code execution workspaces)

### 2. Environment Variables
Create a `.env` file in the root directory (based on `.env.example`):
OPENAI_API_KEY=your_key_here
JARVIS_API_KEY=optional_auth_key

### 3. Start Backend
Run the following in PowerShell:
virtualenv venv
.\venv\Scripts\Activate.ps1
pip install -e .
$env:PYTHONPATH="src"
uvicorn jarvis.api.main:app --host 0.0.0.0 --port 8000

### 4. Start Frontend
cd frontend
npm install
npm run build
npm run preview

### 5. Running Tests
The test suite utilizes deterministic mock models and isolated SQLite transactions to verify task workflows, concurrent executions, and recovery processes offline.
$env:PYTHONPATH="src"
pytest tests/ -v

## Docker Compose Deployment
docker-compose up --build
*Note: The docker-compose configuration mounts the Docker socket to allow JARVIS to dynamically spawn sandboxes. Ensure this aligns with your security posture.*
