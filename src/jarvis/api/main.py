from fastapi import FastAPI, HTTPException, Depends, Security, UploadFile, File, Response
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
import os
from typing import List, Optional
from contextlib import asynccontextmanager

from jarvis.repository import TaskRepository
from jarvis.execution.service import ExecutionService
from jarvis.execution.supervisor import Supervisor
from jarvis.execution.worker import DurableWorker
from jarvis.providers import get_provider
from jarvis.workers import WorkerManager
from jarvis.approvals import ApprovalRequest, ApprovalStatus
from jarvis.tasks import Task, TaskStatus
from jarvis.voice import voice_provider

API_KEY = os.environ.get("JARVIS_API_KEY", "")
API_KEY_NAME = "Authorization"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if not API_KEY:
        # Dev mode: No auth required if env var is empty
        return None

    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")

try:
    worker_manager = WorkerManager()
except RuntimeError as e:
    worker_manager = None
    print(f"Warning: WorkerManager initialization failed: {e}")

db_path = "data/jarvis.db"
provider = get_provider("mock")
repo = TaskRepository(db_path)
exec_service = ExecutionService(repo)
supervisor = Supervisor(exec_service, provider, worker_manager)
background_worker = DurableWorker(db_path, supervisor)

@asynccontextmanager
async def lifespan(app: FastAPI):
    background_worker.start()
    yield
    background_worker.stop()

app = FastAPI(title="JARVIS API", version="0.1.0", lifespan=lifespan)

class TaskCreate(BaseModel):
    description: str

class TaskResponse(BaseModel):
    task_id: str
    description: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None

class ApprovalAction(BaseModel):
    action: str  # 'approve' or 'reject'
    user_id: str

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "docker_enabled": worker_manager.use_docker if worker_manager else False
    }

@app.get("/tasks", response_model=List[TaskResponse])
def get_all_tasks(api_key: str = Depends(get_api_key)):
    with repo._get_connection() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 50").fetchall()
        tasks = []
        for row in rows:
            task_dict = dict(row)
            tasks.append(TaskResponse(
                task_id=task_dict["task_id"],
                description=task_dict["description"],
                status=task_dict["status"],
                result=task_dict["result"],
                error=task_dict["error"]
            ))
        return tasks

@app.post("/tasks", response_model=TaskResponse)
def submit_task(request: TaskCreate, api_key: str = Depends(get_api_key)):
    task = exec_service.submit(request.description)
    # Task is picked up by durable worker via DB polling
    return TaskResponse(**task.__dict__)

@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, api_key: str = Depends(get_api_key)):
    task = repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task.__dict__)

@app.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str, api_key: str = Depends(get_api_key)):
    task = repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        exec_service.transition(task_id, TaskStatus.CANCELLED)
        return {"status": "cancelled"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@app.post("/approvals/{request_id}")
def resolve_approval(request_id: str, action: ApprovalAction, api_key: str = Depends(get_api_key)):
    approval = repo.get_approval(request_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Approval no longer pending")

    if action.action == "approve":
        approval.approve(action.user_id)
        repo.update_approval(approval)

        # Resume task logic
        task = repo.get_task(approval.task_id)
        task.history.append({"approved_action": approval.action})
        repo.update_task(task)

        exec_service.transition(task.task_id, TaskStatus.RUNNING)
        # Task resumed via durable worker DB polling

    elif action.action == "reject":
        approval.reject(action.user_id)
        repo.update_approval(approval)
        exec_service.fail(approval.task_id, "Approval rejected by human")
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    return {"status": approval.status.value, "resolved_by": approval.resolved_by}

@app.post("/voice/transcribe")
async def transcribe_voice(file: UploadFile = File(...), api_key: str = Depends(get_api_key)):
    content = await file.read()
    text = voice_provider.transcribe(content)
    return {"text": text}

@app.post("/voice/synthesize")
async def synthesize_voice(request: TaskCreate, api_key: str = Depends(get_api_key)):
    audio_bytes = voice_provider.synthesize(request.description)
    return Response(content=audio_bytes, media_type="audio/mpeg")
