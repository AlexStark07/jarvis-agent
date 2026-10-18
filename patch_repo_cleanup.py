import re

with open('src/jarvis/repository.py', 'r') as f:
    content = f.read()

# Clean up duplicate table creation
duplicate = """                    CREATE TABLE IF NOT EXISTS approval_requests (
                        request_id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        target TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        resolved_at TEXT,
                        resolved_by TEXT
                    );"""

content = content.replace(duplicate, "", 1)

with open('src/jarvis/repository.py', 'w') as f:
    f.write(content)
