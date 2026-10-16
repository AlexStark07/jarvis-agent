import unittest

from jarvis.tasks import (
    InvalidTaskTransition,
    Task,
    TaskStatus,
)
from jarvis.events import ExecutionEvent


class TaskTests(unittest.TestCase):
    def test_task_starts_queued(self):
        task = Task(description="Run a safe verification")
        self.assertEqual(task.status, TaskStatus.QUEUED)
        self.assertTrue(task.task_id)
        self.assertEqual(len(task.history), 1)

    def test_valid_task_lifecycle(self):
        task = Task(description="Verify a result")
        task.transition(TaskStatus.PLANNING)
        task.transition(TaskStatus.RUNNING)
        task.transition(TaskStatus.VERIFYING)
        task.transition(TaskStatus.SUCCEEDED)

        self.assertEqual(task.status, TaskStatus.SUCCEEDED)
        self.assertEqual(len(task.history), 5)

    def test_terminal_state_cannot_restart(self):
        task = Task(description="Verify a result")
        task.transition(TaskStatus.CANCELLED)

        with self.assertRaises(InvalidTaskTransition):
            task.transition(TaskStatus.RUNNING)

    def test_invalid_transition_is_rejected(self):
        task = Task(description="Verify a result")

        with self.assertRaises(InvalidTaskTransition):
            task.transition(TaskStatus.SUCCEEDED)

    def test_empty_description_is_rejected(self):
        with self.assertRaises(ValueError):
            Task(description="   ")

    def test_execution_event(self):
        event = ExecutionEvent(
            task_id="task-001",
            event_type="task.started",
            status="running",
            agent_id="research",
        )
        self.assertEqual(event.task_id, "task-001")
        self.assertTrue(event.event_id)

    def test_event_requires_task_id(self):
        with self.assertRaises(ValueError):
            ExecutionEvent(
                task_id="",
                event_type="task.started",
                status="running",
            )


if __name__ == "__main__":
    unittest.main()
