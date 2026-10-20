import logging
from typing import List, Dict, Any
from jarvis.agents.base import Agent, AgentInput, AgentOutput
from jarvis.tools import registry

logger = logging.getLogger(__name__)

class BaseSpecialist(Agent):
    """Base class abstracting the LLM tool-calling loop logic for specialists."""

    def _execute_loop(self, inputs: AgentInput, system_prompt: str) -> AgentOutput:
        tools = registry.get_langchain_tools(self.allowed_tools)

        prompt = inputs.description
        if "approved_action" in inputs.context:
            prompt += f"\n[System: You were just approved to execute {inputs.context['approved_action']} - please do so now]"

        messages = []
        max_iterations = 5

        for iteration in range(max_iterations):
            logger.info(f"Agent {self.agent_id} executing iteration {iteration + 1}/{max_iterations} for task {inputs.task_id}")
            # Check for cancellation before calling provider
            current_task = self.execution_service.get_task(inputs.task_id) if hasattr(self, 'execution_service') and self.execution_service else None
            if current_task and current_task.status.value == "cancelled":
                 logger.warning(f"Task {inputs.task_id} was cancelled. Aborting agent execution.")
                 return AgentOutput(task_id=inputs.task_id, status="failed", result="", error="Task was cancelled")

            # Format history for provider context (simplified for MVP)
            response = self.provider.generate(prompt, system=system_prompt, tools=tools)

            # Direct string fallback check
            if isinstance(response, str):
                return AgentOutput(task_id=inputs.task_id, status="success", result=response)

            if not getattr(response, 'tool_calls', None) or len(response.tool_calls) == 0:
                if "failed" in response.content.lower():
                    return AgentOutput(task_id=inputs.task_id, status="failed", result="", error=response.content)

                return AgentOutput(
                    task_id=inputs.task_id,
                    status="success",
                    result=response.content
                )

            tool_outputs_collected = []

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                if tool_name not in self.allowed_tools:
                    logger.error(f"Agent {self.agent_id} attempted to use unauthorized tool {tool_name}")
                    return AgentOutput(task_id=inputs.task_id, status="failed", result="", error=f"Unauthorized tool: {tool_name}")

                tool_config = registry.get_tool(tool_name)

                # Halt for human approval if required
                if tool_config and tool_config.requires_approval and not inputs.context.get("approved_action") == tool_name:
                    # Prevent duplicate execution: check if we've already asked for approval in context history
                    if inputs.context.get("pending_action") and inputs.context["pending_action"].get("action") == tool_name:
                         logger.warning(f"Task {inputs.task_id} encountered duplicate approval request for {tool_name}")
                         return AgentOutput(task_id=inputs.task_id, status="failed", result="", error=f"Duplicate approval requested for {tool_name}")

                    logger.info(f"Task {inputs.task_id} pausing for approval on {tool_name}")
                    return AgentOutput(
                        task_id=inputs.task_id,
                        status="waiting_for_approval",
                        result=f"Action requires approval: {tool_name}",
                        requires_approval=True,
                        pending_action={"action": tool_name, "target": str(tool_args)}
                    )

                context_kwargs = {}
                if tool_name == "execute_command":
                    context_kwargs["worker_manager"] = self.worker_manager

                kwargs = {**tool_args, **context_kwargs}
                logger.info(f"Agent {self.agent_id} executing tool {tool_name} for task {inputs.task_id}")
                exec_result = registry.execute(tool_name, kwargs)

                if not exec_result.success:
                    logger.error(f"Tool {tool_name} failed: {exec_result.error}")
                    return AgentOutput(task_id=inputs.task_id, status="failed", result="", error=exec_result.error)

                tool_outputs_collected.append(f"Tool `{tool_name}` output: {exec_result.output}")

            prompt += "\n" + "\n".join(tool_outputs_collected)

        logger.error(f"Agent {self.agent_id} exceeded max iterations (5) for task {inputs.task_id}")
        return AgentOutput(task_id=inputs.task_id, status="failed", result="", error="Max tool iterations exceeded.")

class ResearchAgent(BaseSpecialist):
    @property
    def agent_id(self) -> str: return "research"

    @property
    def allowed_tools(self) -> List[str]: return ["web_search", "read_document"]

    def execute(self, inputs: AgentInput) -> AgentOutput:
        return self._execute_loop(inputs, system_prompt="You are a research agent. Retrieve facts and summarize findings using tools.")

class DeveloperAgent(BaseSpecialist):
    @property
    def agent_id(self) -> str: return "developer"

    @property
    def allowed_tools(self) -> List[str]: return ["write_file", "run_tests", "execute_command"]

    def execute(self, inputs: AgentInput) -> AgentOutput:
        return self._execute_loop(inputs, system_prompt="You are a developer agent. Inspect workspaces and write code safely.")

class OperationsAgent(BaseSpecialist):
    @property
    def agent_id(self) -> str: return "operations"

    @property
    def allowed_tools(self) -> List[str]: return ["check_health", "modify_infrastructure", "desktop_preview_action"]

    def execute(self, inputs: AgentInput) -> AgentOutput:
        return self._execute_loop(inputs, system_prompt="You are an operations agent handling infrastructure.")

class CommunicationsAgent(BaseSpecialist):
    @property
    def agent_id(self) -> str: return "communications"

    @property
    def allowed_tools(self) -> List[str]: return ["send_message"]

    def execute(self, inputs: AgentInput) -> AgentOutput:
        return self._execute_loop(inputs, system_prompt="You are a communications agent. Ensure drafts are approved before dispatch.")

class QASecurityAgent(BaseSpecialist):
    @property
    def agent_id(self) -> str: return "qa_security"

    @property
    def allowed_tools(self) -> List[str]: return ["run_security_scan", "validate_output"]

    def execute(self, inputs: AgentInput) -> AgentOutput:
        return self._execute_loop(inputs, system_prompt="You are a QA and Security validation agent.")
