import re

with open('tests/test_api.py', 'r') as f:
    content = f.read()

new_content = """import tempfile
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

    time.sleep(0.5)

    task = repo.get_task(task_id)
    assert task.status == TaskStatus.WAITING_FOR_APPROVAL

    row = repo._connection.execute("SELECT request_id FROM approval_requests WHERE task_id = ?", (task_id,)).fetchone()
    assert row is not None
    req_id = row["request_id"]

    # Resolve approval
    resp = client.post(f"/approvals/{req_id}", json={"action": "approve", "user_id": "admin_1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    time.sleep(0.5)

    # Verify task resumed and succeeded
    task_after = repo.get_task(task_id)
    assert task_after.status == TaskStatus.SUCCEEDED
"""

with open('tests/test_api.py', 'w') as f:
    f.write(new_content)
