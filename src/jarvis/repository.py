import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from jarvis.events import ExecutionEvent
from jarvis.tasks import Task, TaskStatus
from jarvis.approvals import ApprovalRequest, ApprovalStatus

def _datetime(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)

class ConcurrentTaskUpdateError(Exception):
    pass

class TaskRepository:
    def __init__(self, database_path: str | Path = "data/jarvis.db") -> None:
        self.database_path = str(database_path)

        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(
                parents=True, exist_ok=True
            )

        self._initialize()

    @contextmanager
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
            conn.close()

    def _initialize(self) -> None:
        with self._get_connection() as conn:
            with conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        description TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        assigned_agent_id TEXT,
                        result TEXT,
                        error TEXT,
                        history_json TEXT NOT NULL,
                        version INTEGER DEFAULT 0,
                        locked_by TEXT,
                        locked_until TEXT
                    );

                    CREATE TABLE IF NOT EXISTS execution_events (
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
                    );


                """)

    def create_task(self, task: Task) -> None:
        with self._get_connection() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO tasks (
                        task_id, description, status, created_at, updated_at,
                        assigned_agent_id, result, error, history_json, version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.task_id,
                        task.description,
                        task.status.value,
                        task.created_at.isoformat(),
                        task.updated_at.isoformat(),
                        task.assigned_agent_id,
                        task.result,
                        task.error,
                        json.dumps(task.history),
                        task.version,
                    ),
                )

    def get_tasks_by_status(self, statuses: list[str]) -> list[Task]:
        with self._get_connection() as conn:
            placeholders = ','.join('?' for _ in statuses)
            rows = conn.execute(
                f"SELECT * FROM tasks WHERE status IN ({placeholders}) ORDER BY created_at ASC",
                statuses,
            ).fetchall()

            tasks = []
            for row in rows:
                task = Task(description=row["description"])
                task.task_id = row["task_id"]
                task.status = TaskStatus(row["status"])
                task.created_at = _datetime(row["created_at"])
                task.updated_at = _datetime(row["updated_at"])
                task.assigned_agent_id = row["assigned_agent_id"]
                task.result = row["result"]
                task.error = row["error"]
                task.history = json.loads(row["history_json"]) if row["history_json"] else []
                task.version = row["version"]
                tasks.append(task)

            return tasks

    def get_task(self, task_id: str) -> Task | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()

            if row is None:
                return None

            task = Task(description=row["description"])
            task.task_id = row["task_id"]
            task.status = TaskStatus(row["status"])
            task.created_at = _datetime(row["created_at"])
            task.updated_at = _datetime(row["updated_at"])
            task.assigned_agent_id = row["assigned_agent_id"]
            task.result = row["result"]
            task.error = row["error"]
            task.history = json.loads(row["history_json"]) if row["history_json"] else []
            task.version = row["version"]
            return task

    def update_task(self, task: Task) -> None:
        with self._get_connection() as conn:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE tasks SET
                        description = ?,
                        status = ?,
                        updated_at = ?,
                        assigned_agent_id = ?,
                        result = ?,
                        error = ?,
                        history_json = ?,
                        version = version + 1
                    WHERE task_id = ? AND version = ?
                    """,
                    (
                        task.description,
                        task.status.value,
                        task.updated_at.isoformat(),
                        task.assigned_agent_id,
                        task.result,
                        task.error,
                        json.dumps(task.history),
                        task.task_id,
                        task.version,
                    ),
                )

                if cursor.rowcount != 1:
                    exists = conn.execute(
                        "SELECT 1 FROM tasks WHERE task_id = ?", (task.task_id,)
                    ).fetchone()
                    if exists:
                        raise ConcurrentTaskUpdateError(
                            f"Task {task.task_id} was updated by another process."
                        )
                    raise KeyError(f"Task not found: {task.task_id}")

                task.version += 1

    def record_event(self, event: ExecutionEvent) -> None:
        with self._get_connection() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO execution_events (
                        event_id, task_id, event_type, status, agent_id,
                        parent_event_id, occurred_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.task_id,
                        event.event_type,
                        event.status,
                        event.agent_id,
                        event.parent_event_id,
                        event.occurred_at.isoformat(),
                        json.dumps(event.metadata),
                    ),
                )

    def create_approval(self, approval: ApprovalRequest) -> None:
        with self._get_connection() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO approval_requests (
                        request_id, task_id, action, target, status,
                        created_at, resolved_at, resolved_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        approval.request_id,
                        approval.task_id,
                        approval.action,
                        approval.target,
                        approval.status.value,
                        approval.created_at.isoformat(),
                        approval.resolved_at.isoformat() if approval.resolved_at else None,
                        approval.resolved_by,
                    ),
                )

    def get_approval(self, request_id: str) -> ApprovalRequest | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM approval_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()

            if row is None:
                return None

            return ApprovalRequest(
                request_id=row["request_id"],
                task_id=row["task_id"],
                action=row["action"],
                target=row["target"],
                status=ApprovalStatus(row["status"]),
                created_at=_datetime(row["created_at"]),
                resolved_at=_datetime(row["resolved_at"]) if row["resolved_at"] else None,
                resolved_by=row["resolved_by"],
            )

    def update_approval(self, approval: ApprovalRequest) -> None:
        with self._get_connection() as conn:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE approval_requests SET
                        status = ?,
                        resolved_at = ?,
                        resolved_by = ?
                    WHERE request_id = ?
                    """,
                    (
                        approval.status.value,
                        approval.resolved_at.isoformat() if approval.resolved_at else None,
                        approval.resolved_by,
                        approval.request_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise KeyError(f"Approval not found: {approval.request_id}")

    def list_events(self, task_id: str) -> list[ExecutionEvent]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM execution_events
                WHERE task_id = ?
                ORDER BY occurred_at, rowid
                """,
                (task_id,),
            ).fetchall()

            return [
                ExecutionEvent(
                    task_id=row["task_id"],
                    event_type=row["event_type"],
                    status=row["status"],
                    agent_id=row["agent_id"],
                    parent_event_id=row["parent_event_id"],
                    event_id=row["event_id"],
                    occurred_at=_datetime(row["occurred_at"]),
                    metadata=json.loads(row["metadata_json"]),
                )
                for row in rows
            ]

    def create_task_with_event(
        self, task: Task, event: ExecutionEvent
    ) -> None:
        if task.task_id != event.task_id:
            raise ValueError("Task and event IDs must match.")

        with self._get_connection() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO tasks (
                        task_id, description, status, created_at, updated_at,
                        assigned_agent_id, result, error, history_json, version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.task_id,
                        task.description,
                        task.status.value,
                        task.created_at.isoformat(),
                        task.updated_at.isoformat(),
                        task.assigned_agent_id,
                        task.result,
                        task.error,
                        json.dumps(task.history),
                        task.version,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO execution_events (
                        event_id, task_id, event_type, status, agent_id,
                        parent_event_id, occurred_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.task_id,
                        event.event_type,
                        event.status,
                        event.agent_id,
                        event.parent_event_id,
                        event.occurred_at.isoformat(),
                        json.dumps(event.metadata),
                    ),
                )

    def save_task_with_event(
        self, task: Task, event: ExecutionEvent
    ) -> None:
        if task.task_id != event.task_id:
            raise ValueError("Task and event IDs must match.")

        with self._get_connection() as conn:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE tasks SET
                        description = ?,
                        status = ?,
                        updated_at = ?,
                        assigned_agent_id = ?,
                        result = ?,
                        error = ?,
                        history_json = ?,
                        version = version + 1
                    WHERE task_id = ? AND version = ?
                    """,
                    (
                        task.description,
                        task.status.value,
                        task.updated_at.isoformat(),
                        task.assigned_agent_id,
                        task.result,
                        task.error,
                        json.dumps(task.history),
                        task.task_id,
                        task.version,
                    ),
                )

                if cursor.rowcount != 1:
                    exists = conn.execute(
                        "SELECT 1 FROM tasks WHERE task_id = ?", (task.task_id,)
                    ).fetchone()
                    if exists:
                        raise ConcurrentTaskUpdateError(
                            f"Task {task.task_id} was updated by another process."
                        )
                    raise KeyError(f"Task not found: {task.task_id}")

                task.version += 1

                conn.execute(
                    """
                    INSERT INTO execution_events (
                        event_id, task_id, event_type, status, agent_id,
                        parent_event_id, occurred_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.task_id,
                        event.event_type,
                        event.status,
                        event.agent_id,
                        event.parent_event_id,
                        event.occurred_at.isoformat(),
                        json.dumps(event.metadata),
                    ),
                )

    def close(self) -> None:
        pass

    def __enter__(self) -> "TaskRepository":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        pass

    def claim_task(self, task_id: str, worker_id: str, lease_duration: int = 60) -> bool:
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        locked_until = (now + timedelta(seconds=lease_duration)).isoformat()

        with self._get_connection() as conn:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE tasks
                    SET locked_by = ?, locked_until = ?
                    WHERE task_id = ? AND (locked_until IS NULL OR locked_until < ?)
                    """,
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
                    """
                    UPDATE tasks
                    SET locked_until = ?
                    WHERE task_id = ? AND locked_by = ?
                    """,
                    (locked_until, task_id, worker_id)
                )
                return cursor.rowcount == 1

    def release_task(self, task_id: str, worker_id: str) -> None:
        with self._get_connection() as conn:
            with conn:
                conn.execute(
                    """
                    UPDATE tasks
                    SET locked_by = NULL, locked_until = NULL
                    WHERE task_id = ? AND locked_by = ?
                    """,
                    (task_id, worker_id)
                )