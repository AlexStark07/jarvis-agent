import unittest
from jarvis.agents.base import AgentInput
from jarvis.agents.specialists import ResearchAgent, DeveloperAgent, OperationsAgent, CommunicationsAgent, QASecurityAgent
from jarvis.providers import MockProvider
from langchain_core.messages import AIMessage, ToolCall

class TestSpecialists(unittest.TestCase):
    def setUp(self):
        self.worker_manager = None

    def test_research_agent(self):
        provider = MockProvider(sequence=[
            AIMessage(content="", tool_calls=[ToolCall(name="web_search", args={"query": "Research test"}, id="call_1")]), AIMessage(content="Mock Research Finding")
        ])
        agent = ResearchAgent(provider)
        output = agent.execute(AgentInput(task_id="1", description="Research test"))
        if output.status != "success":
            print(output.error)
        self.assertEqual(output.status, "success")
        self.assertIn("Mock Research Finding", output.result)

    def test_developer_agent_code(self):
        provider = MockProvider(sequence=[
            AIMessage(content="", tool_calls=[ToolCall(name="write_file", args={"path": "test.py", "content": "Code"}, id="call_1")]), AIMessage(content="Code Changes completed.")
        ])
        agent = DeveloperAgent(provider)
        output = agent.execute(AgentInput(task_id="1", description="Write code"))
        if output.status != "success":
            print(output.error)
        self.assertEqual(output.status, "success")
        self.assertIn("Code Changes", output.result)

    def test_operations_agent_requires_approval_for_deploy(self):
        provider = MockProvider(sequence=[
            AIMessage(
                content="",
                tool_calls=[ToolCall(name="modify_infrastructure", args={"target": "production"}, id="call_1")]
            )
        ])
        agent = OperationsAgent(provider)
        output = agent.execute(AgentInput(task_id="1", description="Deploy to production"))
        self.assertEqual(output.status, "waiting_for_approval")
        self.assertTrue(output.requires_approval)

    def test_qa_security_agent_fails_on_unsafe(self):
        provider = MockProvider(sequence=[
            AIMessage(
                content="",
                tool_calls=[ToolCall(name="validate_output", args={"is_safe": False, "reason": "Unsafe request detected"}, id="call_1")]
            )
        ])
        agent = QASecurityAgent(provider)
        output = agent.execute(AgentInput(task_id="1", description="Execute unsafe command"))
        self.assertEqual(output.status, "failed")
        self.assertIn("Unsafe request detected", output.error)


    def test_agent_invalid_tool(self):
        from langchain_core.messages import AIMessage, ToolCall
        provider = MockProvider(sequence=[
            AIMessage(
                content="",
                tool_calls=[ToolCall(name="unknown_tool", args={"target": "production"}, id="call_1")]
            )
        ])
        agent = OperationsAgent(provider)
        output = agent.execute(AgentInput(task_id="1", description="Deploy to production"))
        self.assertEqual(output.status, "failed")
        self.assertIn("Unauthorized tool: unknown_tool", output.error)

    def test_agent_tool_failure(self):
        from langchain_core.messages import AIMessage, ToolCall
        provider = MockProvider(sequence=[
            AIMessage(
                content="",
                tool_calls=[ToolCall(name="check_health", args={}, id="call_1")]
            )
        ])
        agent = OperationsAgent(provider)
        output = agent.execute(AgentInput(task_id="1", description="Check health without args"))
        self.assertEqual(output.status, "failed")

    def test_desktop_preview_requires_approval(self):
        from langchain_core.messages import AIMessage, ToolCall
        provider = MockProvider(sequence=[
            AIMessage(
                content="",
                tool_calls=[ToolCall(name="desktop_preview_action", args={"action_type": "open_app", "target_data": "calculator"}, id="call_1")]
            )
        ])
        agent = OperationsAgent(provider)
        output = agent.execute(AgentInput(task_id="1", description="Open calculator"))
        self.assertEqual(output.status, "waiting_for_approval")
        self.assertTrue(output.requires_approval)
        self.assertEqual(output.pending_action["action"], "desktop_preview_action")

if __name__ == "__main__":
    unittest.main()
