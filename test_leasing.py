import tempfile
import os
from pathlib import Path
from jarvis.repository import TaskRepository
from jarvis.tasks import Task, TaskStatus

with tempfile.TemporaryDirectory() as temp:
    db = str(Path(temp) / "jarvis.db")
    repo = TaskRepository(db)

    t = Task(description="Lease testing")
    repo.create_task(t)

    # Claim successfully
    success = repo.claim_task(t.task_id, "worker_1")
    assert success

    # Cannot be claimed by another worker
    fail = repo.claim_task(t.task_id, "worker_2")
    assert not fail

    # Can be renewed by same worker
    renew = repo.renew_lease(t.task_id, "worker_1")
    assert renew

    # Release successfully
    repo.release_task(t.task_id, "worker_1")

    # Can be claimed by another worker now
    success2 = repo.claim_task(t.task_id, "worker_2")
    assert success2

    print("Leasing works perfectly")
