import pytest
import time
import tempfile
import threading
from pathlib import Path

from jarvis.repository import TaskRepository
from jarvis.tasks import Task, TaskStatus

def test_competing_task_claims():
    with tempfile.TemporaryDirectory() as temp:
        db = str(Path(temp) / "jarvis.db")
        repo1 = TaskRepository(db)
        repo2 = TaskRepository(db)

        t = Task(description="Claim test")
        repo1.create_task(t)

        # Worker 1 claims
        success1 = repo1.claim_task(t.task_id, "worker_1")
        assert success1

        # Worker 2 tries to claim at same time
        success2 = repo2.claim_task(t.task_id, "worker_2")
        assert not success2

def test_expired_lease_recovery():
    with tempfile.TemporaryDirectory() as temp:
        db = str(Path(temp) / "jarvis.db")
        repo = TaskRepository(db)

        t = Task(description="Expiry test")
        repo.create_task(t)

        # Claim with very short lease
        repo.claim_task(t.task_id, "worker_1", lease_duration=1)

        # Immediate attempt fails
        assert not repo.claim_task(t.task_id, "worker_2")

        # Wait for expiry
        time.sleep(1.1)

        # Can now be claimed
        assert repo.claim_task(t.task_id, "worker_2")

def test_simultaneous_read_write():
    # Because of WAL, reads should not block writes and vice versa
    with tempfile.TemporaryDirectory() as temp:
        db = str(Path(temp) / "jarvis.db")
        repo = TaskRepository(db)

        t = Task(description="RW test")
        repo.create_task(t)

        # Hold a read cursor
        with repo._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tasks")

            # Use another repo instance to update
            repo2 = TaskRepository(db)
            t.transition(TaskStatus.PLANNING)
            repo2.update_task(t)

            # Read still works
            row = cursor.fetchone()
            assert row is not None


def test_worker_restart_recovery():
    from jarvis.execution.worker import DurableWorker
    from jarvis.execution.supervisor import Supervisor
    from jarvis.execution.service import ExecutionService
    from jarvis.providers import MockProvider
    from langchain_core.messages import AIMessage

    with tempfile.TemporaryDirectory() as temp:
        db = str(Path(temp) / "jarvis.db")
        repo = TaskRepository(db)

        # Setup mock that pauses execution via sleep
        provider = MockProvider(sequence=[
            AIMessage(content="Simulated long work")
        ])

        exec_service = ExecutionService(repo)
        supervisor = Supervisor(exec_service, provider, None)

        worker1 = DurableWorker(db, supervisor, poll_interval=0.1)
        worker1.start()

        t = exec_service.submit("long running task")

        # Wait for worker 1 to claim it
        start = time.time()
        while time.time() - start < 1.0:
            task = repo.get_task(t.task_id)
            if task.status.value in ["planning", "running", "verifying", "succeeded"]:
                break
            time.sleep(0.05)

        # Crash worker 1
        worker1.stop()

        # Worker 2 boots up and runs recovery
        worker2 = DurableWorker(db, supervisor, poll_interval=0.1)
        worker2.start()

        # Check that it continues and finishes the task
        start = time.time()
        while time.time() - start < 2.0:
            task = repo.get_task(t.task_id)
            if task.status.value == "succeeded":
                break
            time.sleep(0.05)

        worker2.stop()
        task_final = repo.get_task(t.task_id)
        assert task_final.status.value == "succeeded"
