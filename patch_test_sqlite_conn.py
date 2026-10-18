import re

with open('tests/test_api.py', 'r') as f:
    content = f.read()

# Fix repo queries accessing internal _connection directly, now we need to use context manager
new_query = """    with repo._get_connection() as conn:
        row = conn.execute("SELECT request_id FROM approval_requests WHERE task_id = ?", (task_id,)).fetchone()"""

content = content.replace("    row = repo._connection.execute(\"SELECT request_id FROM approval_requests WHERE task_id = ?\", (task_id,)).fetchone()", new_query)

with open('tests/test_api.py', 'w') as f:
    f.write(content)

with open('tests/test_workflow.py', 'r') as f:
    content = f.read()

content = content.replace("    row = repo._connection.execute(\"SELECT request_id FROM approval_requests WHERE task_id = ?\", (task_id,)).fetchone()", new_query)

with open('tests/test_workflow.py', 'w') as f:
    f.write(content)
