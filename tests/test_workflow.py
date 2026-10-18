import pytest
import time
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from jarvis.api.main import app, repo
from jarvis.tasks import TaskStatus
from jarvis.approvals import ApprovalRequest
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

        from jarvis.api.main import background_worker
        # Give worker its own path
        background_worker.repo_path = db
        background_worker.poll_interval = 0.05

        # Stop and clear the worker from previous tests
        background_worker.stop()
        background_worker._thread = None
        background_worker._stop_event.clear()
        background_worker._active_tasks.clear()
        background_worker.start()

        yield
        background_worker.stop()
        repo.database_path = original_db
        jarvis.providers._MOCK_SEQUENCE.clear()
        from jarvis.api.main import provider
        provider.call_count = 0

def wait_for_status(task_id: str, desired_status: str, timeout: float = 2.0):
    start = time.time()
    while time.time() - start < timeout:
        resp = client.get(f"/tasks/{task_id}")
        if resp.json().get("status") == desired_status:
            return resp.json()
        time.sleep(0.05)
    resp = client.get(f"/tasks/{task_id}")
    return resp.json()

def test_e2e_successful_sync_task():
    from langchain_core.messages import AIMessage, ToolCall

    # 1. Plan: route to research
    # 2. Research agent executes
    # 3. QA verify
    jarvis.providers._MOCK_SEQUENCE.extend([
        AIMessage(content="research"),
        AIMessage(content="", tool_calls=[ToolCall(name="web_search", args={"query": "search for information"}, id="call_1")]),
        AIMessage(content="Mock Research Finding"),
        AIMessage(content="QA Passed")
    ])

    resp = client.post("/tasks", json={"description": "search for information"})
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]

    data = wait_for_status(task_id, TaskStatus.SUCCEEDED.value)
    assert data["status"] == TaskStatus.SUCCEEDED.value
    assert "Mock Research Finding" in data["result"]
    assert "QA Passed" in data["result"]

def test_e2e_approval_task_flow():
    from langchain_core.messages import AIMessage, ToolCall

    # Plan: route to operations
    # Ops agent issues deploy tool call
    # Pause for approval...
    # (After approval) Resume Ops agent: confirm action
    # Verify QA
    jarvis.providers._MOCK_SEQUENCE.extend([
        AIMessage(content="operations"),
        AIMessage(
            content="",
            tool_calls=[ToolCall(name="modify_infrastructure", args={"target": "production"}, id="call_1")]
        ),
        AIMessage(content="Resumed and executed deploy new server"),
        AIMessage(content="QA Passed")
    ])

    resp = client.post("/tasks", json={"description": "deploy new server"})
    task_id = resp.json()["task_id"]

    task_data = wait_for_status(task_id, TaskStatus.WAITING_FOR_APPROVAL.value)
    assert task_data["status"] == TaskStatus.WAITING_FOR_APPROVAL.value

    # Add a slight retry to fetch the row from sqlite
    for _ in range(10):
        with repo._get_connection() as conn:
            row = conn.execute("SELECT request_id FROM approval_requests WHERE task_id = ?", (task_id,)).fetchone()
            if row:
                break
        time.sleep(0.05)
    assert row is not None
    req_id = row["request_id"]

    app_resp = client.post(f"/approvals/{req_id}", json={"action": "approve", "user_id": "tester"})
    assert app_resp.status_code == 200

    final_data = wait_for_status(task_id, TaskStatus.SUCCEEDED.value)
    assert final_data["status"] == TaskStatus.SUCCEEDED.value
    assert "Resumed and executed deploy new server" in final_data["result"]

def test_e2e_safety_rejection():
    from langchain_core.messages import AIMessage, ToolCall

    # Plan: route to qa_security
    # QA agent rejects
    jarvis.providers._MOCK_SEQUENCE.extend([
        AIMessage(content="qa_security"),
        AIMessage(
            content="",
            tool_calls=[ToolCall(name="validate_output", args={"is_safe": False, "reason": "Unsafe request detected"}, id="call_1")]
        )
    ])

    resp = client.post("/tasks", json={"description": "validate unsafe code injection"})
    task_id = resp.json()["task_id"]

    data = wait_for_status(task_id, TaskStatus.FAILED.value)
    assert data["status"] == TaskStatus.FAILED.value
    assert "QA Validation Failed: Unsafe request detected" in data.get("error", "") or "Unsafe request detected" in data.get("error", "")
