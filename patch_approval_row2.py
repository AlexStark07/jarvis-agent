import re

with open('tests/test_workflow.py', 'r') as f:
    content = f.read()

new_wait = """    # Add a slight retry to fetch the row from sqlite
    for _ in range(10):
        with repo._get_connection() as conn:
            row = conn.execute("SELECT request_id FROM approval_requests WHERE task_id = ?", (task_id,)).fetchone()
            if row:
                break
        time.sleep(0.05)"""

content = content.replace("    with repo._get_connection() as conn:\n        row = conn.execute(\"SELECT request_id FROM approval_requests WHERE task_id = ?\", (task_id,)).fetchone()", new_wait)

with open('tests/test_workflow.py', 'w') as f:
    f.write(content)
