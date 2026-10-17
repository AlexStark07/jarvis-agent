import re

with open('tests/test_agents.py', 'r') as f:
    content = f.read()

new_content = """import unittest
from jarvis.agents.base import AgentInput
from jarvis.agents.specialists import ResearchAgent, DeveloperAgent, OperationsAgent, CommunicationsAgent, QASecurityAgent
from jarvis.providers import MockProvider
from langchain_core.messages import AIMessage, ToolCall

class TestSpecialists(unittest.TestCase):
    def setUp(self):
        self.worker_manager = None

    def test_research_agent(self):
        provider = MockProvider(sequence=[
            AIMessage(content="Mock Research Finding")
        ])
        agent = ResearchAgent(provider)
        output = agent.execute(AgentInput(task_id="1", description="Research test"))
        self.assertEqual(output.status, "success")
        self.assertIn("Mock Research Finding", output.result)

    def test_developer_agent_code(self):
        provider = MockProvider(sequence=[
            AIMessage(content="Code Changes completed.")
        ])
        agent = DeveloperAgent(provider)
        output = agent.execute(AgentInput(task_id="1", description="Write code"))
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

if __name__ == "__main__":
    unittest.main()
"""

with open('tests/test_agents.py', 'w') as f:
    f.write(new_content)
