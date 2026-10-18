import re

with open('src/jarvis/execution/supervisor.py', 'r') as f:
    content = f.read()

# Protect against failing a cancelled task. We check if the status is already cancelled
new_fail = """    def _node_fail(self, state: SupervisorState) -> SupervisorState:
        # Prevent failing an already cancelled task
        task = self.execution_service.get_task(state["task_id"])
        if task and task.status.value != "cancelled":
             self.execution_service.fail(state["task_id"], state["error"] or "Task failed.")
        return state"""

content = re.sub(r'    def _node_fail\(self, state: SupervisorState\) -> SupervisorState:.*?        return state', new_fail, content, flags=re.DOTALL)

with open('src/jarvis/execution/supervisor.py', 'w') as f:
    f.write(content)
