import pytest
from fastapi.testclient import TestClient
import io
import os
import tempfile
from pathlib import Path

from jarvis.api.main import app, repo
from jarvis.voice import voice_provider

@pytest.fixture(autouse=True)
def setup_teardown():
    with tempfile.TemporaryDirectory() as temp:
        db = str(Path(temp) / "jarvis_api.db")
        original_db = repo.database_path
        repo.database_path = db
        repo._initialize()

        from jarvis.api.main import background_worker, exec_service
        background_worker.repo_path = db
        background_worker.poll_interval = 0.05

        background_worker.stop()
        background_worker._thread = None
        background_worker._stop_event.clear()
        background_worker._active_tasks.clear()
        background_worker.start()

        yield
        background_worker.stop()
        repo.database_path = original_db
        import jarvis.providers
        jarvis.providers._MOCK_SEQUENCE.clear()
        from jarvis.api.main import provider
        provider.call_count = 0

client = TestClient(app)

def test_voice_transcribe():
    file_content = b"fake audio data"
    response = client.post(
        "/voice/transcribe",
        files={"file": ("test.wav", io.BytesIO(file_content), "audio/wav")}
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Simulated voice input text"

def test_voice_synthesize():
    response = client.post(
        "/voice/synthesize",
        json={"description": "Hello JARVIS"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert b"Simulated voice audio bytes for: Hello JARVIS" in response.content
