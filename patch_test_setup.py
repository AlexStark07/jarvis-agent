import re

with open('tests/test_api.py', 'r') as f:
    content = f.read()

# Since we use FastAPI TestClient natively, it doesn't trigger lifespan events.
# We need to manually start the worker instance attached to the test database.
new_setup = """@pytest.fixture(autouse=True)
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
        provider.call_count = 0"""

content = re.sub(r'@pytest\.fixture\(autouse=True\).*?provider\.call_count = 0', new_setup, content, flags=re.DOTALL)

with open('tests/test_api.py', 'w') as f:
    f.write(content)

with open('tests/test_workflow.py', 'r') as f:
    content = f.read()

content = re.sub(r'@pytest\.fixture\(autouse=True\).*?provider\.call_count = 0', new_setup, content, flags=re.DOTALL)

with open('tests/test_workflow.py', 'w') as f:
    f.write(content)
