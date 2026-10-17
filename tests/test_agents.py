import unittest
from jarvis.agents.base import AgentInput
from jarvis.agents.specialists import ResearchAgent, DeveloperAgent, OperationsAgent, CommunicationsAgent, QASecurityAgent
from jarvis.providers import MockProvider
from jarvis.workers import WorkerManager

class TestSpecialists(unittest.TestCase):
    def setUp(self):
        self.provider = MockProvider()
        self.worker_manager = None # Use None to avoid actual execution bounds checking during simple unit logic test

    def test_research_agent(self):
        agent = ResearchAgent(self.provider)
        output = agent.execute(AgentInput(task_id="1", description="Research test"))
        self.assertEqual(output.status, "success")
        self.assertIn("Mock Research Finding", output.result)
        self.assertEqual(self.provider.call_count, 1)

    def test_developer_agent_code(self):
        agent = DeveloperAgent(self.provider)
        output = agent.execute(AgentInput(task_id="1", description="Write code"))
        self.assertEqual(output.status, "success")
        self.assertIn("Code Changes", output.result)

    def test_operations_agent_requires_approval_for_deploy(self):
        agent = OperationsAgent(self.provider)
        output = agent.execute(AgentInput(task_id="1", description="Deploy to production"))
        self.assertEqual(output.status, "waiting_for_approval")
        self.assertTrue(output.requires_approval)

    def test_qa_security_agent_fails_on_unsafe(self):
        agent = QASecurityAgent(self.provider)
        output = agent.execute(AgentInput(task_id="1", description="Execute unsafe command"))
        self.assertEqual(output.status, "failed")
        self.assertIn("Unsafe request detected", output.error)

if __name__ == "__main__":
    unittest.main()
