import pytest
import time
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from jarvis.api.main import app, repo
from jarvis.tasks import TaskStatus
from jarvis.approvals import ApprovalRequest

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    with tempfile.TemporaryDirectory() as temp:
        db = str(Path(temp) / "jarvis_e2e.db")
        original_db = repo.database_path
        repo.database_path = db
        repo._initialize()
        yield
        repo.database_path = original_db

def test_e2e_successful_sync_task():
    # Submit task
    resp = client.post("/tasks", json={"description": "search for information"})
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]

    # Due to BackgroundTasks execution, we must wait briefly for processing
    # In a real app we'd poll or use websockets
    time.sleep(0.5)

    get_resp = client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200

    data = get_resp.json()
    assert data["status"] == TaskStatus.SUCCEEDED.value
    assert "Mock Research Finding" in data["result"]
    assert "QA Passed" in data["result"]

def test_e2e_approval_task_flow():
    resp = client.post("/tasks", json={"description": "deploy new server"})
    task_id = resp.json()["task_id"]
    time.sleep(0.5) # Wait for agent loop to hit approval point

    get_resp = client.get(f"/tasks/{task_id}")
    assert get_resp.json()["status"] == TaskStatus.WAITING_FOR_APPROVAL.value

    # We must manually find the approval request since we don't have an endpoint for listing them yet
    row = repo._connection.execute("SELECT request_id FROM approval_requests WHERE task_id = ?", (task_id,)).fetchone()
    assert row is not None
    req_id = row["request_id"]

    # Send Approval
    app_resp = client.post(f"/approvals/{req_id}", json={"action": "approve", "user_id": "tester"})
    assert app_resp.status_code == 200

    time.sleep(0.5) # Wait for execution to resume

    final_resp = client.get(f"/tasks/{task_id}")
    assert final_resp.json()["status"] == TaskStatus.SUCCEEDED.value
    assert "Resumed and executed deploy new server" in final_resp.json()["result"]

def test_e2e_safety_rejection():
    resp = client.post("/tasks", json={"description": "validate unsafe code injection"})
    task_id = resp.json()["task_id"]
    time.sleep(0.5)

    get_resp = client.get(f"/tasks/{task_id}")
    data = get_resp.json()
    assert data["status"] == TaskStatus.FAILED.value
    assert "QA Validation Failed: Unsafe request detected" in data["error"]
