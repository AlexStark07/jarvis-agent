from typing import Dict, Any

from jarvis.execution.service import ExecutionService
from jarvis.tasks import Task, TaskStatus
from jarvis.agents.base import Agent, AgentInput
from jarvis.agents.specialists import (
    ResearchAgent, DeveloperAgent, OperationsAgent,
    CommunicationsAgent, QASecurityAgent
)

class Supervisor:
    """Orchestrates tasks across specialist agents."""

    def __init__(self, execution_service: ExecutionService, provider: Any, worker_manager: Any | None = None):
        self.execution_service = execution_service
        self.provider = provider
        self.worker_manager = worker_manager

        # Initialize specialists
        self.specialists: Dict[str, Agent] = {
            "research": ResearchAgent(provider, worker_manager),
            "developer": DeveloperAgent(provider, worker_manager),
            "operations": OperationsAgent(provider, worker_manager),
            "communications": CommunicationsAgent(provider, worker_manager),
            "qa_security": QASecurityAgent(provider, worker_manager),
        }

    def _determine_agent(self, description: str) -> str:
        """Route task to the appropriate specialist based on content."""
        lower_desc = description.lower()
        if "research" in lower_desc or "search" in lower_desc:
            return "research"
        elif "deploy" in lower_desc or "infrastructure" in lower_desc:
            return "operations"
        elif "email" in lower_desc or "message" in lower_desc:
            return "communications"
        elif "unsafe" in lower_desc or "validate" in lower_desc:
            return "qa_security"
        return "developer" # Default to developer for general logic

    def process_task(self, task_id: str) -> Task:
        """Execute a single processing loop for a task."""
        task = self.execution_service.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        if task.status == TaskStatus.QUEUED:
            task = self.execution_service.transition(task.task_id, TaskStatus.PLANNING)

        if task.status == TaskStatus.PLANNING:
            agent_id = self._determine_agent(task.description)
            task = self.execution_service.assign_agent(task.task_id, agent_id)
            task = self.execution_service.transition(task.task_id, TaskStatus.RUNNING)

        if task.status == TaskStatus.RUNNING:
            agent = self.specialists[task.assigned_agent_id]

            # Check context from history
            context = {}
            for entry in reversed(task.history):
                if "approved_action" in entry:
                    context["approved_action"] = entry["approved_action"]
                    break

            inputs = AgentInput(task_id=task.task_id, description=task.description, context=context)

            try:
                output = agent.execute(inputs)

                if output.status == "waiting_for_approval":
                    task = self.execution_service.transition(task.task_id, TaskStatus.WAITING_FOR_APPROVAL)
                    # For resuming, we append to history to track it
                    if output.pending_action:
                        task.history.append({"pending_action": output.pending_action})
                        self.execution_service.repository.update_task(task)
                    return task
                elif output.status == "failed":
                    return self.execution_service.fail(task.task_id, output.error or "Unknown error")

                # On success, move to verifying via QA agent unless it was the QA agent
                if task.assigned_agent_id != "qa_security":
                    task = self.execution_service.transition(task.task_id, TaskStatus.VERIFYING)

                    # QA Validation
                    qa = self.specialists["qa_security"]
                    qa_out = qa.execute(AgentInput(task_id=task.task_id, description=f"Validate: {output.result}"))

                    if qa_out.status == "failed":
                        return self.execution_service.fail(task.task_id, qa_out.error or "QA Failed")
                else:
                     task = self.execution_service.transition(task.task_id, TaskStatus.VERIFYING)

                return self.execution_service.complete(task.task_id, output.result)

            except Exception as e:
                return self.execution_service.fail(task.task_id, f"Execution exception: {str(e)}")

        return task
