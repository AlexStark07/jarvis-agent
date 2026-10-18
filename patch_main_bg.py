import re

with open('src/jarvis/api/main.py', 'r') as f:
    content = f.read()

# Replace background tasks imports and usage with DurableWorker logic
new_imports = """from fastapi import FastAPI, HTTPException, Depends
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
from jarvis.tasks import Task, TaskStatus"""

content = re.sub(r'from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks\nfrom pydantic import BaseModel\nfrom typing import List, Optional\n\nfrom jarvis\.repository import TaskRepository\nfrom jarvis\.execution\.service import ExecutionService\nfrom jarvis\.execution\.supervisor import Supervisor\nfrom jarvis\.providers import get_provider\nfrom jarvis\.workers import WorkerManager\nfrom jarvis\.approvals import ApprovalRequest, ApprovalStatus\nfrom jarvis\.tasks import Task, TaskStatus', new_imports, content, flags=re.DOTALL)

# Add lifespan initialization
worker_init = """try:
    worker_manager = WorkerManager()
except RuntimeError as e:
    worker_manager = None
    print(f"Warning: WorkerManager initialization failed: {e}")

db_path = "data/jarvis.db"
repo = TaskRepository(db_path)
exec_service = ExecutionService(repo)
supervisor = Supervisor(exec_service, provider, worker_manager)
background_worker = DurableWorker(db_path, supervisor)

@asynccontextmanager
async def lifespan(app: FastAPI):
    background_worker.start()
    yield
    background_worker.stop()

app = FastAPI(title="JARVIS API", version="0.1.0", lifespan=lifespan)"""

content = re.sub(r'app = FastAPI\(title="JARVIS API", version="0\.1\.0"\).*?supervisor = Supervisor\(exec_service, provider, worker_manager\)', worker_init, content, flags=re.DOTALL)


# Remove BackgroundTasks injection from submit
content = re.sub(r'def submit_task\(request: TaskCreate, background_tasks: BackgroundTasks\):\n    task = exec_service\.submit\(request\.description\)\n    # Fire and forget execution trigger off main thread\n    background_tasks\.add_task\(supervisor\.process_task, task\.task_id\)', r'def submit_task(request: TaskCreate):\n    task = exec_service.submit(request.description)\n    # Task is picked up by durable worker via DB polling', content)

# Remove BackgroundTasks injection from resolve_approval
content = re.sub(r'def resolve_approval\(request_id: str, action: ApprovalAction, background_tasks: BackgroundTasks\):', r'def resolve_approval(request_id: str, action: ApprovalAction):', content)
content = re.sub(r'        exec_service\.transition\(task\.task_id, TaskStatus\.RUNNING\)\n        background_tasks\.add_task\(supervisor\.process_task, task\.task_id\)', r'        exec_service.transition(task.task_id, TaskStatus.RUNNING)\n        # Task resumed via durable worker DB polling', content)

with open('src/jarvis/api/main.py', 'w') as f:
    f.write(content)
