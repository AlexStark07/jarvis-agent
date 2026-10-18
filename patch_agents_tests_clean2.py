with open('tests/test_agents.py', 'r') as f:
    content = f.read()

import re

# Extract the poorly placed functions
functions = """    def test_agent_invalid_tool(self):
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
        self.assertEqual(output.status, "failed")"""

content = re.sub(r'if __name__ == "__main__":\n    unittest\.main\(\).*', '', content, flags=re.DOTALL)
content = content + "\n" + functions + "\n\nif __name__ == \"__main__\":\n    unittest.main()\n"

with open('tests/test_agents.py', 'w') as f:
    f.write(content)
