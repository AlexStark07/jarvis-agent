import os
if "JARVIS_API_KEY" in os.environ:
    del os.environ["JARVIS_API_KEY"]
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

        from jarvis.api.main import background_worker, exec_service
        import jarvis.api.main
        jarvis.api.main.repo = repo
        background_worker.repo_path = db
        background_worker.supervisor.execution_service.repository = repo
        exec_service.repository = repo

        background_worker.poll_interval = 0.05

        background_worker.stop()
        background_worker._thread = None
        background_worker._stop_event.clear()
        background_worker._active_tasks.clear()
        background_worker.start()

        import jarvis.providers
        jarvis.providers._MOCK_SEQUENCE.clear()
        from jarvis.api.main import provider
        provider.call_count = 0

        yield

        background_worker.stop()
        background_worker._thread = None
        background_worker._stop_event.clear()
        background_worker._active_tasks.clear()
        repo.database_path = original_db
        jarvis.providers._MOCK_SEQUENCE.clear()

    # To fix "pytest tests/ -v" state leakage from test_voice etc
    import jarvis.providers
    jarvis.providers._MOCK_SEQUENCE.clear()

def wait_for_status(task_id: str, desired_status: str, timeout: float = 5.0):
    start = time.time()
    while time.time() - start < timeout:
        res = client.get(f"/tasks/{task_id}")
        if res.status_code != 200:
            print("ERROR GETTING TASK:", res.status_code, res.json())
        resp = res.json()
        if resp.get("status") == desired_status:
            return resp
        time.sleep(0.05)
    return client.get(f"/tasks/{task_id}").json()

def test_e2e_successful_sync_task():
    import jarvis.providers
    jarvis.providers._MOCK_SEQUENCE.clear()
    from jarvis.api.main import provider
    provider.call_count = 0
    from langchain_core.messages import AIMessage, ToolCall
    import jarvis.providers

    # 1. Plan: route to research
    # 2. Research agent executes
    # 3. QA verify
    jarvis.providers._MOCK_SEQUENCE.extend([
        AIMessage(content="research"),
        AIMessage(content="", tool_calls=[ToolCall(name="web_search", args={"query": "search for information"}, id="call_1")]),
        AIMessage(content="Mock Research Finding"),
        AIMessage(content="QA Passed")
    ])

    # Submit task
    resp = client.post("/tasks", json={"description": "search for information"})
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]

    data = wait_for_status(task_id, TaskStatus.SUCCEEDED.value, timeout=10.0)
    if data["status"] != TaskStatus.SUCCEEDED.value:
        print("FAILED TASK DATA:", data)
    assert data["status"] == TaskStatus.SUCCEEDED.value
    assert "Mock Research Finding" in data["result"]
    assert "QA Passed" in data["result"]

def test_e2e_approval_task_flow():
    from langchain_core.messages import AIMessage, ToolCall
    import jarvis.providers

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

    # We must manually find the approval request since we don't have an endpoint for listing them yet
    for _ in range(50):
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
    import jarvis.providers

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
    assert "Unsafe request detected" in data["error"]
