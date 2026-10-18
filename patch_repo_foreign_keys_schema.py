import re

with open('src/jarvis/repository.py', 'r') as f:
    content = f.read()

# Make the events table actually define the foreign key!
new_schema = """                    CREATE TABLE IF NOT EXISTS execution_events (
                        event_id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        agent_id TEXT,
                        parent_event_id TEXT,
                        occurred_at TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS approval_requests (
                        request_id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        target TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        resolved_at TEXT,
                        resolved_by TEXT,
                        FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                    );"""

content = re.sub(r'                    CREATE TABLE IF NOT EXISTS execution_events \(.*?                    \);', new_schema, content, flags=re.DOTALL)

with open('src/jarvis/repository.py', 'w') as f:
    f.write(content)
