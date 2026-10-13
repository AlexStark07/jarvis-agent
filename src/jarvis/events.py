from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ExecutionEvent:
    task_id: str
    event_type: str
    status: str
    agent_id: str | None = None
    parent_event_id: str | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id cannot be empty.")
        if not self.event_type.strip():
            raise ValueError("event_type cannot be empty.")
        if not self.status.strip():
            raise ValueError("status cannot be empty.")
