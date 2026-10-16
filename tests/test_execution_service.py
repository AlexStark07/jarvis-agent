import tempfile
import unittest
from pathlib import Path

from jarvis.execution.service import ExecutionService
from jarvis.repository import TaskRepository
from jarvis.tasks import TaskStatus


class ExecutionServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = TaskRepository(
            str(Path(self.temp.name) / "jarvis.db")
        )
        self.service = ExecutionService(self.repo)

    def tearDown(self):
        self.repo.close()
        self.temp.cleanup()

    def test_submit_persists_task_and_creation_event(self):
        task = self.service.submit("Inspect a document")

        stored = self.service.get_task(task.task_id)
        events = self.service.get_events(task.task_id)

        self.assertIsNotNone(stored)
        self.assertEqual(stored.status, TaskStatus.QUEUED)
        self.assertEqual(events[0].event_type, "task.created")

    def test_full_lifecycle_records_events_and_result(self):
        task = self.service.submit("Calculate a result")
        self.service.transition(task.task_id, TaskStatus.PLANNING)
        self.service.assign_agent(task.task_id, "research")
        self.service.transition(task.task_id, TaskStatus.RUNNING)
        self.service.transition(task.task_id, TaskStatus.VERIFYING)
        completed = self.service.complete(
            task.task_id,
            "Verified result",
        )

        self.assertEqual(completed.status, TaskStatus.SUCCEEDED)
        self.assertEqual(completed.result, "Verified result")

        events = self.service.get_events(task.task_id)
        self.assertEqual(events[-1].event_type, "task.completed")
        self.assertEqual(len(events), 6)

    def test_completion_requires_verifying_state(self):
        task = self.service.submit("Premature completion")

        with self.assertRaises(ValueError):
            self.service.complete(task.task_id, "Not ready")

    def test_failure_is_persisted(self):
        task = self.service.submit("Task that fails")
        self.service.transition(task.task_id, TaskStatus.PLANNING)
        failed = self.service.fail(task.task_id, "Controlled test failure")

        recovered = self.service.get_task(task.task_id)
        self.assertEqual(failed.status, TaskStatus.FAILED)
        self.assertEqual(recovered.status, TaskStatus.FAILED)
        self.assertEqual(recovered.error, "Controlled test failure")

    def test_unknown_task_is_rejected(self):
        with self.assertRaises(KeyError):
            self.service.transition("unknown", TaskStatus.PLANNING)

    def test_blank_result_is_rejected(self):
        task = self.service.submit("Empty result")
        self.service.transition(task.task_id, TaskStatus.PLANNING)
        self.service.transition(task.task_id, TaskStatus.RUNNING)
        self.service.transition(task.task_id, TaskStatus.VERIFYING)

        with self.assertRaises(ValueError):
            self.service.complete(task.task_id, "  ")


if __name__ == "__main__":
    unittest.main()
