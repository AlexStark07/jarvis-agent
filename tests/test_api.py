import tempfile
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import time

from jarvis.api.main import app, repo, exec_service, supervisor
from jarvis.approvals import ApprovalRequest, ApprovalStatus
from jarvis.tasks import TaskStatus
import jarvis.providers

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    # Use a fresh in-memory database for API tests
    with tempfile.TemporaryDirectory() as temp:
        db = str(Path(temp) / "jarvis_api.db")
        # Override the app's repo temporarily for tests
        original_db = repo.database_path
        repo.database_path = db
        repo._initialize()
        yield
        repo.database_path = original_db
        jarvis.providers._MOCK_SEQUENCE.clear()
        from jarvis.api.main import provider
        provider.call_count = 0


def wait_for_status(task_id: str, desired_status: TaskStatus, timeout: float = 2.0):
    start = time.time()
    while time.time() - start < timeout:
        task = repo.get_task(task_id)
        if task.status == desired_status:
            return task
        time.sleep(0.05)
    return repo.get_task(task_id)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_submit_task():
    response = client.post("/tasks", json={"description": "test task"})
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] in ["succeeded", "verifying", "running", "queued", "planning"]

def test_submit_and_get_task():
    # Create
    create_resp = client.post("/tasks", json={"description": "search testing"})
    task_id = create_resp.json()["task_id"]

    # Retrieve
    get_resp = client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["task_id"] == task_id

def test_approval_workflow():
    from langchain_core.messages import AIMessage, ToolCall
    jarvis.providers._MOCK_SEQUENCE.extend([
        AIMessage(content="operations"),
        AIMessage(
            content="",
            tool_calls=[ToolCall(name="modify_infrastructure", args={"target": "production"}, id="call_1")]
        ),
        AIMessage(content="Deploy finished"),
        AIMessage(content="QA passed")
    ])

    # Simulate a task that requires an approval (Operations deploy)
    create_resp = client.post("/tasks", json={"description": "Deploy to infra"})
    task_id = create_resp.json()["task_id"]

    task = wait_for_status(task_id, TaskStatus.WAITING_FOR_APPROVAL)
    assert task.status == TaskStatus.WAITING_FOR_APPROVAL

    row = repo._connection.execute("SELECT request_id FROM approval_requests WHERE task_id = ?", (task_id,)).fetchone()
    assert row is not None
    req_id = row["request_id"]

    # Resolve approval
    resp = client.post(f"/approvals/{req_id}", json={"action": "approve", "user_id": "admin_1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # Verify task resumed and succeeded
    task_after = wait_for_status(task_id, TaskStatus.SUCCEEDED)
    assert task_after.status == TaskStatus.SUCCEEDED

def test_approval_rejection_workflow():
    from langchain_core.messages import AIMessage, ToolCall
    import time

    # Needs to hit operations, ask for approval, then rejection fails the task
    jarvis.providers._MOCK_SEQUENCE.extend([
        AIMessage(content="operations"),
        AIMessage(
            content="",
            tool_calls=[ToolCall(name="modify_infrastructure", args={"target": "production"}, id="call_1")]
        )
    ])

    create_resp = client.post("/tasks", json={"description": "Deploy to infra reject"})
    task_id = create_resp.json()["task_id"]

    task = wait_for_status(task_id, TaskStatus.WAITING_FOR_APPROVAL)
    assert task.status == TaskStatus.WAITING_FOR_APPROVAL

    row = repo._connection.execute("SELECT request_id FROM approval_requests WHERE task_id = ?", (task_id,)).fetchone()
    assert row is not None
    req_id = row["request_id"]

    # Resolve approval with rejection
    resp = client.post(f"/approvals/{req_id}", json={"action": "reject", "user_id": "admin_1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    # Verify task failed
    task_after = wait_for_status(task_id, TaskStatus.FAILED)
    assert task_after.status == TaskStatus.FAILED
    assert "Approval rejected by human" in task_after.error

def test_cancellation():
    from langchain_core.messages import AIMessage, ToolCall
    import time

    # We add a tool call that asks for approval so the task naturally pauses in WAITING_FOR_APPROVAL
    jarvis.providers._MOCK_SEQUENCE.extend([
        AIMessage(content="operations"),
        AIMessage(
            content="",
            tool_calls=[ToolCall(name="modify_infrastructure", args={"target": "production"}, id="call_1")]
        )
    ])

    # We create a task
    resp = client.post("/tasks", json={"description": "task to cancel"})
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]

    task = wait_for_status(task_id, TaskStatus.WAITING_FOR_APPROVAL)

    cancel_resp = client.post(f"/tasks/{task_id}/cancel")
    assert cancel_resp.status_code == 200

    task_after = repo.get_task(task_id)
    assert task_after.status == TaskStatus.CANCELLED
