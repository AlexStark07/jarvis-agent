import threading
import time
import logging
import uuid
from jarvis.repository import TaskRepository
from jarvis.tasks import TaskStatus
from jarvis.execution.supervisor import Supervisor

logger = logging.getLogger(__name__)

class DurableWorker:
    def __init__(self, repo_path: str, supervisor: Supervisor, poll_interval: float = 1.0):
        self.repo_path = repo_path
        self.supervisor = supervisor
        self.poll_interval = poll_interval
        self.worker_id = str(uuid.uuid4())
        self._stop_event = threading.Event()
        self._thread = None
        self._active_tasks = set()
        self._lock = threading.Lock()

    def start(self):
        if self._thread is not None:
            return

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"DurableWorker {self.worker_id} started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info(f"DurableWorker {self.worker_id} stopped.")

    def _run_loop(self):
        repo = TaskRepository(self.repo_path)
        while not self._stop_event.is_set():
            try:
                tasks = repo.get_tasks_by_status([
                    TaskStatus.QUEUED.value,
                    TaskStatus.RUNNING.value,
                    TaskStatus.PLANNING.value,
                    TaskStatus.VERIFYING.value
                ])
                for task in tasks:
                    if self._stop_event.is_set():
                        break

                    with self._lock:
                        if task.task_id in self._active_tasks:
                            continue

                    # Attempt atomic claim
                    if repo.claim_task(task.task_id, self.worker_id, lease_duration=60):
                        with self._lock:
                            self._active_tasks.add(task.task_id)
                        threading.Thread(target=self._process_wrapper, args=(task.task_id,), daemon=True).start()

            except Exception as e:
                logger.error(f"Error in DurableWorker loop: {e}")

            self._stop_event.wait(self.poll_interval)

    def _process_wrapper(self, task_id: str):
        repo = TaskRepository(self.repo_path)
        # Background lease renewer
        stop_renewal = threading.Event()
        def renewer():
            while not stop_renewal.is_set():
                if stop_renewal.wait(30):
                    break
                repo.renew_lease(task_id, self.worker_id, lease_duration=60)

        renewal_thread = threading.Thread(target=renewer, daemon=True)
        renewal_thread.start()

        try:
            self.supervisor.process_task(task_id)
        except Exception as e:
            logger.error(f"Execution failed for task {task_id}: {e}")
            try:
                task = repo.get_task(task_id)
                if task and task.status not in [TaskStatus.FAILED, TaskStatus.SUCCEEDED, TaskStatus.CANCELLED]:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    repo.update_task(task)
            except Exception as inner_e:
                 logger.error(f"Failed to cleanly fail task {task_id}: {inner_e}")
        finally:
            stop_renewal.set()
            renewal_thread.join(timeout=2.0)
            repo.release_task(task_id, self.worker_id)
            with self._lock:
                if task_id in self._active_tasks:
                    self._active_tasks.remove(task_id)
