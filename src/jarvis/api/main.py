from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
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
    return {"status": "ok", "docker_enabled": worker_manager.use_docker}

@app.post("/tasks", response_model=TaskResponse)
def submit_task(request: TaskCreate):
    task = exec_service.submit(request.description)
    # Task is picked up by durable worker via DB polling
    return TaskResponse(**task.__dict__)

@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str):
    task = repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task.__dict__)

@app.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str):
    task = repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        exec_service.transition(task_id, TaskStatus.CANCELLED)
        return {"status": "cancelled"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@app.post("/approvals/{request_id}")
def resolve_approval(request_id: str, action: ApprovalAction):
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
