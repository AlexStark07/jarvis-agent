import re

with open('src/jarvis/repository.py', 'r') as f:
    content = f.read()

new_methods = """    def claim_task(self, task_id: str, worker_id: str, lease_duration: int = 60) -> bool:
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        locked_until = (now + timedelta(seconds=lease_duration)).isoformat()

        with self._get_connection() as conn:
            with conn:
                cursor = conn.execute(
                    \"\"\"
                    UPDATE tasks
                    SET locked_by = ?, locked_until = ?
                    WHERE task_id = ? AND (locked_until IS NULL OR locked_until < ?)
                    \"\"\",
                    (worker_id, locked_until, task_id, now.isoformat())
                )
                return cursor.rowcount == 1

    def renew_lease(self, task_id: str, worker_id: str, lease_duration: int = 60) -> bool:
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        locked_until = (now + timedelta(seconds=lease_duration)).isoformat()

        with self._get_connection() as conn:
            with conn:
                cursor = conn.execute(
                    \"\"\"
                    UPDATE tasks
                    SET locked_until = ?
                    WHERE task_id = ? AND locked_by = ?
                    \"\"\",
                    (locked_until, task_id, worker_id)
                )
                return cursor.rowcount == 1

    def release_task(self, task_id: str, worker_id: str) -> None:
        with self._get_connection() as conn:
            with conn:
                conn.execute(
                    \"\"\"
                    UPDATE tasks
                    SET locked_by = NULL, locked_until = NULL
                    WHERE task_id = ? AND locked_by = ?
                    \"\"\",
                    (task_id, worker_id)
                )"""

content = content + "\n" + new_methods

with open('src/jarvis/repository.py', 'w') as f:
    f.write(content)
