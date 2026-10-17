from typing import List
from jarvis.agents.base import Agent, AgentInput, AgentOutput

class ResearchAgent(Agent):
    @property
    def agent_id(self) -> str: return "research"

    @property
    def allowed_tools(self) -> List[str]: return ["web_search", "read_document"]

    def execute(self, inputs: AgentInput) -> AgentOutput:
        response = self.provider.generate(f"Research request: {inputs.description}")
        return AgentOutput(
            task_id=inputs.task_id,
            status="success",
            result=f"Research Findings:\n{response}"
        )

class DeveloperAgent(Agent):
    @property
    def agent_id(self) -> str: return "developer"

    @property
    def allowed_tools(self) -> List[str]: return ["write_file", "run_tests"]

    def execute(self, inputs: AgentInput) -> AgentOutput:
        # Utilize worker manager if specific dev commands were requested
        if self.worker_manager and "execute" in inputs.description.lower():
            workspace = self.worker_manager.create_workspace()
            res = self.worker_manager.execute(["python", "-c", "print('Executed safely')"], workspace)
            return AgentOutput(
                task_id=inputs.task_id,
                status="success",
                result=f"Execution result: {res.stdout}"
            )

        response = self.provider.generate(f"Developer task: {inputs.description}")
        return AgentOutput(
            task_id=inputs.task_id,
            status="success",
            result=f"Code Changes:\n{response}"
        )

class OperationsAgent(Agent):
    @property
    def agent_id(self) -> str: return "operations"

    @property
    def allowed_tools(self) -> List[str]: return ["check_health", "modify_infrastructure"]

    def execute(self, inputs: AgentInput) -> AgentOutput:
        # Check if we're resuming a previously approved infrastructure action
        if inputs.context.get("approved_action") == "modify_infrastructure":
            return AgentOutput(
                task_id=inputs.task_id,
                status="success",
                result=f"Ops Status:\nResumed and executed {inputs.description}"
            )

        if "deploy" in inputs.description.lower() or "infrastructure" in inputs.description.lower():
            return AgentOutput(
                task_id=inputs.task_id,
                status="waiting_for_approval",
                result="Action requires approval.",
                requires_approval=True,
                pending_action={"action": "modify_infrastructure", "target": inputs.description}
            )

        response = self.provider.generate(f"Ops request: {inputs.description}")
        return AgentOutput(
            task_id=inputs.task_id,
            status="success",
            result=f"Ops Status:\n{response}"
        )

class CommunicationsAgent(Agent):
    @property
    def agent_id(self) -> str: return "communications"

    @property
    def allowed_tools(self) -> List[str]: return ["send_email", "post_message"]

    def execute(self, inputs: AgentInput) -> AgentOutput:
        return AgentOutput(
            task_id=inputs.task_id,
            status="waiting_for_approval",
            result="Draft prepared. Pending approval to send.",
            requires_approval=True,
            pending_action={"action": "send_message", "draft": inputs.description}
        )

class QASecurityAgent(Agent):
    @property
    def agent_id(self) -> str: return "qa_security"

    @property
    def allowed_tools(self) -> List[str]: return ["run_security_scan", "validate_output"]

    def execute(self, inputs: AgentInput) -> AgentOutput:
        response = self.provider.generate(f"QA Validation: {inputs.description}")
        if "fail" in inputs.description.lower() or "unsafe" in inputs.description.lower():
            return AgentOutput(
                task_id=inputs.task_id,
                status="failed",
                result="",
                error="QA Validation Failed: Unsafe request detected."
            )

        return AgentOutput(
            task_id=inputs.task_id,
            status="success",
            result=f"QA Passed:\n{response}"
        )
