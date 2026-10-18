import re

with open('src/jarvis/repository.py', 'r') as f:
    content = f.read()

# Add PRAGMA foreign_keys=ON to enforce foreign key constraints, otherwise test_event_for_unknown_task_is_rejected fails
new_get_connection = """    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(
            self.database_path,
            timeout=15.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        # Enforce foreign key constraints
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()"""

content = re.sub(r'    @contextmanager\n    def _get_connection.*?finally:\n            conn\.close\(\)', new_get_connection, content, flags=re.DOTALL)

with open('src/jarvis/repository.py', 'w') as f:
    f.write(content)
