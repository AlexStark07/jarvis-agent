from typing import Dict, Any, TypedDict, Literal
from langgraph.graph import StateGraph, START, END

from jarvis.execution.service import ExecutionService
from jarvis.tasks import Task, TaskStatus
from jarvis.agents.base import Agent, AgentInput
from jarvis.agents.specialists import (
    ResearchAgent, DeveloperAgent, OperationsAgent,
    CommunicationsAgent, QASecurityAgent
)

class SupervisorState(TypedDict):
    task_id: str
    description: str
    status: str
    agent_id: str | None
    result: str | None
    error: str | None
    requires_approval: bool
    context: Dict[str, Any]

class Supervisor:
    """Orchestrates tasks across specialist agents using LangGraph."""

    def __init__(self, execution_service: ExecutionService, provider: Any, worker_manager: Any | None = None):
        self.execution_service = execution_service
        self.provider = provider
        self.worker_manager = worker_manager

        self.specialists: Dict[str, Agent] = {
            "research": ResearchAgent(provider, worker_manager, execution_service),
            "developer": DeveloperAgent(provider, worker_manager, execution_service),
            "operations": OperationsAgent(provider, worker_manager, execution_service),
            "communications": CommunicationsAgent(provider, worker_manager, execution_service),
            "qa_security": QASecurityAgent(provider, worker_manager, execution_service),
        }

        # Build LangGraph Workflow
        workflow = StateGraph(SupervisorState)

        # Nodes
        workflow.add_node("plan", self._node_plan)
        workflow.add_node("execute_agent", self._node_execute_agent)
        workflow.add_node("verify", self._node_verify)
        workflow.add_node("wait_approval", self._node_wait_approval)
        workflow.add_node("complete", self._node_complete)
        workflow.add_node("fail", self._node_fail)

        # Edges
        workflow.add_edge(START, "plan")

        def route_after_plan(state: SupervisorState) -> str:
            return "execute_agent"

        workflow.add_conditional_edges("plan", route_after_plan, {"execute_agent": "execute_agent"})

        def route_after_execute(state: SupervisorState) -> str:
            if state["status"] == "failed":
                return "fail"
            elif state["status"] == "waiting_for_approval":
                return "wait_approval"
            # If it was the QA agent executing, skip recursive verification
            elif state["agent_id"] == "qa_security":
                return "complete"
            return "verify"

        workflow.add_conditional_edges("execute_agent", route_after_execute, {
            "fail": "fail",
            "wait_approval": "wait_approval",
            "verify": "verify",
            "complete": "complete"
        })

        def route_after_verify(state: SupervisorState) -> str:
            if state["status"] == "failed":
                return "fail"
            return "complete"

        workflow.add_conditional_edges("verify", route_after_verify, {"fail": "fail", "complete": "complete"})

        workflow.add_edge("wait_approval", END) # Halts graph for human intervention
        workflow.add_edge("complete", END)
        workflow.add_edge("fail", END)

        # Currently keeping SQLite persistence at the task service layer for MVP
        # Checkpointer would wrap `workflow.compile(checkpointer=MemorySaver())`
        self.app = workflow.compile()

    def _node_plan(self, state: SupervisorState) -> SupervisorState:
        prompt = f"Plan task: {state['description']}. Available agents: research, developer, operations, communications, qa_security. Reply with agent_id only."
        response = self.provider.generate(prompt)
        agent_id = response.content.strip().lower()

        if agent_id not in self.specialists:
            agent_id = "developer" # Default fallback

        self.execution_service.assign_agent(state["task_id"], agent_id)
        self.execution_service.transition(state["task_id"], TaskStatus.RUNNING)
        return {"agent_id": agent_id, "status": "running"}

    def _node_execute_agent(self, state: SupervisorState) -> SupervisorState:
        agent = self.specialists[state["agent_id"]]
        inputs = AgentInput(task_id=state["task_id"], description=state["description"], context=state["context"])

        try:
            output = agent.execute(inputs)
            if output.status == "waiting_for_approval":
                self.execution_service.transition(state["task_id"], TaskStatus.WAITING_FOR_APPROVAL)
                task = self.execution_service.get_task(state["task_id"])
                if output.pending_action:
                    from jarvis.approvals import ApprovalRequest
                    approval = ApprovalRequest(
                        task_id=state["task_id"],
                        action=output.pending_action.get("action", "unknown"),
                        target=output.pending_action.get("target", "unknown")
                    )
                    self.execution_service.repository.create_approval(approval)
                    task.history.append({"pending_action": output.pending_action, "request_id": approval.request_id})
                    self.execution_service.repository.update_task(task)
                return {"status": "waiting_for_approval"}

            if output.status == "failed":
                return {"status": "failed", "error": output.error}

            return {"status": "verifying", "result": output.result}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def _node_verify(self, state: SupervisorState) -> SupervisorState:
        self.execution_service.transition(state["task_id"], TaskStatus.VERIFYING)
        qa = self.specialists["qa_security"]
        qa_out = qa.execute(AgentInput(task_id=state["task_id"], description=f"Validate: {state['result']}"))
        if qa_out.status == "failed":
            return {"status": "failed", "error": qa_out.error or "QA Failed"}
        return {"status": "succeeded", "result": f"{state['result']}\n{qa_out.result}"}

    def _node_complete(self, state: SupervisorState) -> SupervisorState:
        self.execution_service.complete(state["task_id"], state["result"] or "Task completed.")
        return {"status": "succeeded"}

    def _node_wait_approval(self, state: SupervisorState) -> SupervisorState:
        # State paused. End of graph thread.
        return state

    def _node_fail(self, state: SupervisorState) -> SupervisorState:
        # Prevent failing an already cancelled task
        task = self.execution_service.get_task(state["task_id"])
        if task and task.status.value != "cancelled":
             self.execution_service.fail(state["task_id"], state["error"] or "Task failed.")
        return state

    def process_task(self, task_id: str) -> None:
        """Trigger the LangGraph workflow for a given task."""
        task = self.execution_service.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        # Reconstruct context for resuming workflows
        context = {}
        for entry in reversed(task.history):
            if "approved_action" in entry:
                context["approved_action"] = entry["approved_action"]
            if "pending_action" in entry:
                context["pending_action"] = entry["pending_action"]

        initial_state = SupervisorState(
            task_id=task.task_id,
            description=task.description,
            status=task.status.value,
            agent_id=task.assigned_agent_id,
            result=task.result,
            error=task.error,
            requires_approval=False,
            context=context
        )

        # Determine starting node based on current task status (to support resumes)
        if task.status == TaskStatus.QUEUED:
            self.execution_service.transition(task.task_id, TaskStatus.PLANNING)
            # Run graph from start
            self.app.invoke(initial_state)
        elif task.status == TaskStatus.RUNNING:
            # Resuming an approved action or retrying. We start the graph from the `execute_agent` node directly.

            # Note: We must temporarily update the state for LangGraph to know we are bypassing "plan"
            initial_state["status"] = "running"

            # Since LangGraph's .invoke() without a checkpointer always starts at START,
            # and we don't have a checkpointer configured yet, we will just call the graph nodes directly based on the DAG flow.
            # This is semantically equivalent to a graph step-through for this stateless execution phase.
            # We must merge partial state dictionaries appropriately.

            current_state = {**initial_state}

            state_update = self._node_execute_agent(current_state)
            current_state = {**current_state, **state_update}

            if current_state["status"] == "failed":
                self._node_fail(current_state)
            elif current_state["status"] == "waiting_for_approval":
                self._node_wait_approval(current_state)
            elif current_state["agent_id"] == "qa_security":
                self._node_complete(current_state)
            else:
                state_update = self._node_verify(current_state)
                current_state = {**current_state, **state_update}

                if current_state["status"] == "failed":
                    self._node_fail(current_state)
                else:
                    self._node_complete(current_state)

        else:
            raise ValueError(f"Cannot process task in state {task.status.value}")
