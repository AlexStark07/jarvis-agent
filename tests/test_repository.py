import tempfile
import unittest
from pathlib import Path

from jarvis.events import ExecutionEvent
from jarvis.repository import TaskRepository
from jarvis.tasks import Task, TaskStatus


class RepositoryTests(unittest.TestCase):
    def test_task_survives_repository_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            db = str(Path(temp) / "jarvis.db")
            task = Task(description="Test durable storage")

            with TaskRepository(db) as repo:
                repo.create_task(task)
                loaded = repo.get_task(task.task_id)
                self.assertIsNotNone(loaded)
                assert loaded is not None
                loaded.transition(TaskStatus.PLANNING)
                repo.update_task(loaded)

            with TaskRepository(db) as repo:
                recovered = repo.get_task(task.task_id)
                self.assertIsNotNone(recovered)
                assert recovered is not None
                self.assertEqual(recovered.status, TaskStatus.PLANNING)
                self.assertEqual(recovered.description, task.description)
                self.assertEqual(len(recovered.history), 2)

    def test_events_are_persisted_and_retrievable(self):
        with tempfile.TemporaryDirectory() as temp:
            db = str(Path(temp) / "jarvis.db")
            task = Task(description="Test event storage")

            with TaskRepository(db) as repo:
                repo.create_task(task)
                event = ExecutionEvent(
                    task_id=task.task_id,
                    event_type="task.started",
                    status="running",
                    agent_id="research",
                    metadata={"attempt": 1},
                )
                repo.record_event(event)

            with TaskRepository(db) as repo:
                events = repo.list_events(task.task_id)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].event_type, "task.started")
                self.assertEqual(events[0].metadata["attempt"], 1)

    def test_duplicate_task_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with TaskRepository(str(Path(temp) / "jarvis.db")) as repo:
                task = Task(description="Duplicate test")
                repo.create_task(task)

                with self.assertRaises(Exception):
                    repo.create_task(task)

    def test_missing_task_returns_none(self):
        with tempfile.TemporaryDirectory() as temp:
            with TaskRepository(str(Path(temp) / "jarvis.db")) as repo:
                self.assertIsNone(repo.get_task("missing-task"))

    def test_event_for_unknown_task_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with TaskRepository(str(Path(temp) / "jarvis.db")) as repo:
                event = ExecutionEvent(
                    task_id="missing-task",
                    event_type="task.started",
                    status="running",
                )
                with self.assertRaises(Exception):
                    repo.record_event(event)
    
    def test_task_update_rolls_back_if_event_insert_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            db = str(Path(temp) / "jarvis.db")

            with TaskRepository(db) as repo:
                task = Task(description="Test update rollback")
                repo.create_task(task)

                existing_event = ExecutionEvent(
                    task_id=task.task_id,
                    event_type="existing",
                    status="queued",
                    event_id="duplicate-event-id",
                )
                repo.record_event(existing_event)

                changed_task = repo.get_task(task.task_id)
                assert changed_task is not None
                changed_task.transition(TaskStatus.PLANNING)

                duplicate_event = ExecutionEvent(
                    task_id=task.task_id,
                    event_type="duplicate",
                    status="planning",
                    event_id="duplicate-event-id",
                )

                with self.assertRaises(Exception):
                    repo.save_task_with_event(changed_task, duplicate_event)

                saved_task = repo.get_task(task.task_id)
                assert saved_task is not None
                self.assertEqual(saved_task.status, TaskStatus.QUEUED)

    def test_task_creation_rolls_back_if_event_insert_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            db = str(Path(temp) / "jarvis.db")

            with TaskRepository(db) as repo:
                original_task = Task(description="Original task")
                repo.create_task(original_task)
                repo.record_event(
                    ExecutionEvent(
                        task_id=original_task.task_id,
                        event_type="existing",
                        status="queued",
                        event_id="duplicate-event-id",
                    )
                )

                new_task = Task(description="Task that should roll back")
                duplicate_event = ExecutionEvent(
                    task_id=new_task.task_id,
                    event_type="task.created",
                    status="queued",
                    event_id="duplicate-event-id",
                )

                with self.assertRaises(Exception):
                    repo.create_task_with_event(new_task, duplicate_event)

                self.assertIsNone(repo.get_task(new_task.task_id))

if __name__ == "__main__":
    unittest.main()
