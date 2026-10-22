import pytest
from fastapi.testclient import TestClient
import os
import tempfile
from pathlib import Path
from jarvis.api.main import app, repo

@pytest.fixture
def auth_client():
    os.environ["JARVIS_API_KEY"] = "supersecret"
    from importlib import reload
    import jarvis.api.main
    reload(jarvis.api.main)
    yield TestClient(jarvis.api.main.app)
    os.environ["JARVIS_API_KEY"] = ""
    reload(jarvis.api.main)

def test_auth_rejection(auth_client):
    response = auth_client.get("/tasks/123")
    assert response.status_code == 403

def test_auth_success(auth_client):
    response = auth_client.get("/tasks/123", headers={"Authorization": "supersecret"})
    # 404 means it passed auth but didn't find task, which is correct
    assert response.status_code == 404
