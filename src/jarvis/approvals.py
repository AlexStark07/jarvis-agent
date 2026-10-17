from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class ApprovalRequest:
    task_id: str
    action: str
    target: str
    request_id: str = field(default_factory=lambda: str(uuid4()))
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=utc_now)
    resolved_at: datetime | None = None
    resolved_by: str | None = None

    def approve(self, user_id: str) -> None:
        self.status = ApprovalStatus.APPROVED
        self.resolved_at = utc_now()
        self.resolved_by = user_id

    def reject(self, user_id: str) -> None:
        self.status = ApprovalStatus.REJECTED
        self.resolved_at = utc_now()
        self.resolved_by = user_id
