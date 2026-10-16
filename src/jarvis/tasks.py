from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = {
    TaskStatus.SUCCEEDED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
}

ALLOWED_TRANSITIONS = {
    TaskStatus.QUEUED: {TaskStatus.PLANNING, TaskStatus.CANCELLED},
    TaskStatus.PLANNING: {
        TaskStatus.RUNNING,
        TaskStatus.WAITING_FOR_APPROVAL,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.RUNNING: {
        TaskStatus.WAITING_FOR_APPROVAL,
        TaskStatus.VERIFYING,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.WAITING_FOR_APPROVAL: {
        TaskStatus.RUNNING,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.VERIFYING: {
        TaskStatus.SUCCEEDED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.SUCCEEDED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


class InvalidTaskTransition(ValueError):
    pass


@dataclass
class Task:
    description: str
    task_id: str = field(default_factory=lambda: str(uuid4()))
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    assigned_agent_id: str | None = None
    result: str | None = None
    error: str | None = None
    history: list[dict[str, str]] = field(default_factory=list)
    version: int = 0


    def __post_init__(self) -> None:
        if not self.description.strip():
            raise ValueError("Task description cannot be empty.")

        if self.status != TaskStatus.QUEUED:
            raise ValueError("New tasks must start in the queued state.")

        self.history.append({
            "status": self.status.value,
            "at": self.created_at.isoformat(),
        })

    def transition(self, new_status: TaskStatus) -> None:
        if new_status not in ALLOWED_TRANSITIONS[self.status]:
            raise InvalidTaskTransition(
                f"Cannot transition task from {self.status.value} "
                f"to {new_status.value}."
            )

        self.status = new_status
        self.updated_at = utc_now()
        self.history.append({
            "status": new_status.value,
            "at": self.updated_at.isoformat(),
        })
