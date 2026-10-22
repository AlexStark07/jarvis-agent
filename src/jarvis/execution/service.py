
from __future__ import annotations

from jarvis.events import ExecutionEvent
from jarvis.repository import TaskRepository
from jarvis.tasks import Task, TaskStatus


class ExecutionService:
    """Coordinates task lifecycle changes and persisted execution events."""

    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def submit(self, description: str) -> Task:
        task = Task(description=description)
        event = self._make_event(
            task,
            "task.created",
            {"status": task.status.value},
        )
        self.repository.create_task_with_event(task, event)
        return task

    def get_task(self, task_id: str) -> Task | None:
        return self.repository.get_task(task_id)

    def get_events(self, task_id: str) -> list[ExecutionEvent]:
        return self.repository.list_events(task_id)

    def assign_agent(self, task_id: str, agent_id: str) -> Task:
        if not agent_id.strip():
            raise ValueError("agent_id cannot be empty.")

        task = self._require_task(task_id)

        if task.status not in {TaskStatus.PLANNING, TaskStatus.RUNNING}:
            raise ValueError(
                f"Cannot assign an agent while task is {task.status.value}."
            )

        task.assigned_agent_id = agent_id
        event = self._make_event(
            task,
            "agent.assigned",
            {"assigned_agent_id": agent_id},
            agent_id=agent_id,
        )
        self.repository.save_task_with_event(task, event)
        return task

    def transition(
        self,
        task_id: str,
        new_status: TaskStatus,
        *,
        agent_id: str | None = None,
    ) -> Task:
        task = self._require_task(task_id)
        previous_status = task.status
        task.transition(new_status)

        event = self._make_event(
            task,
            "task.status_changed",
            {
                "from": previous_status.value,
                "to": new_status.value,
            },
            agent_id=agent_id or task.assigned_agent_id,
        )
        self.repository.save_task_with_event(task, event)
        return task

    def complete(
        self,
        task_id: str,
        result: str,
        *,
        agent_id: str | None = None,
    ) -> Task:
        if not result.strip():
            raise ValueError("A successful task requires a non-empty result.")

        task = self._require_task(task_id)

        if task.status != TaskStatus.VERIFYING:
            raise ValueError(
                "A task must be in verifying state before completion."
            )

        previous_status = task.status
        task.result = result
        task.error = None
        task.transition(TaskStatus.SUCCEEDED)

        event = self._make_event(
            task,
            "task.completed",
            {
                "from": previous_status.value,
                "to": task.status.value,
                "result_present": True,
            },
            agent_id=agent_id or task.assigned_agent_id,
        )
        self.repository.save_task_with_event(task, event)
        return task

    def fail(
        self,
        task_id: str,
        error: str,
        *,
        agent_id: str | None = None,
    ) -> Task:
        if not error.strip():
            raise ValueError("Failure reason cannot be empty.")

        task = self._require_task(task_id)
        previous_status = task.status
        task.transition(TaskStatus.FAILED)
        task.error = error
        task.result = None

        event = self._make_event(
            task,
            "task.failed",
            {
                "from": previous_status.value,
                "to": task.status.value,
                "error": error,
            },
            agent_id=agent_id or task.assigned_agent_id,
        )
        self.repository.save_task_with_event(task, event)
        return task

    def _require_task(self, task_id: str) -> Task:
        task = self.repository.get_task(task_id)
        if task is None:
            raise KeyError(f"Task not found: {task_id}")
        return task

    @staticmethod
    def _make_event(
        task: Task,
        event_type: str,
        metadata: dict[str, object],
        *,
        agent_id: str | None = None,
    ) -> ExecutionEvent:
        return ExecutionEvent(
            task_id=task.task_id,
            event_type=event_type,
            status=task.status.value,
            agent_id=agent_id,
            metadata=metadata,
        )
