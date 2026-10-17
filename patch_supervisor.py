import re

with open('src/jarvis/execution/supervisor.py', 'r') as f:
    content = f.read()

new_node_plan = """    def _node_plan(self, state: SupervisorState) -> SupervisorState:
        prompt = f"Plan task: {state['description']}. Available agents: research, developer, operations, communications, qa_security. Reply with agent_id only."
        response = self.provider.generate(prompt)
        agent_id = response.content.strip().lower()

        if agent_id not in self.specialists:
            agent_id = "developer" # Default fallback

        self.execution_service.assign_agent(state["task_id"], agent_id)
        self.execution_service.transition(state["task_id"], TaskStatus.RUNNING)
        return {"agent_id": agent_id, "status": "running"}"""

content = re.sub(r'    def _node_plan\(self, state: SupervisorState\) -> SupervisorState:.*?return {"agent_id": agent_id, "status": "running"}', new_node_plan, content, flags=re.DOTALL)

with open('src/jarvis/execution/supervisor.py', 'w') as f:
    f.write(content)
