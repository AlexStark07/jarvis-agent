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
    with tempfile.TemporaryDirectory() as temp:
        db = str(Path(temp) / "jarvis_e2e.db")
        original_db = repo.database_path
        repo.database_path = db
        repo._initialize()
        yield
        repo.database_path = original_db
        jarvis.providers._MOCK_SEQUENCE.clear()
        from jarvis.api.main import provider
        provider.call_count = 0

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

    time.sleep(0.5)

    get_resp = client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200

    data = get_resp.json()
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
    time.sleep(0.5)

    get_resp = client.get(f"/tasks/{task_id}")
    assert get_resp.json()["status"] == TaskStatus.WAITING_FOR_APPROVAL.value

    row = repo._connection.execute("SELECT request_id FROM approval_requests WHERE task_id = ?", (task_id,)).fetchone()
    assert row is not None
    req_id = row["request_id"]

    app_resp = client.post(f"/approvals/{req_id}", json={"action": "approve", "user_id": "tester"})
    assert app_resp.status_code == 200

    time.sleep(0.5)

    final_resp = client.get(f"/tasks/{task_id}")
    assert final_resp.json()["status"] == TaskStatus.SUCCEEDED.value
    assert "Resumed and executed deploy new server" in final_resp.json()["result"]

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
    time.sleep(0.5)

    get_resp = client.get(f"/tasks/{task_id}")
    data = get_resp.json()
    assert data["status"] == TaskStatus.FAILED.value
    assert "QA Validation Failed: Unsafe request detected" in data.get("error", "") or "Unsafe request detected" in data.get("error", "")
