with open('src/jarvis/agents/specialists.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "exec_result = registry.execute" in line:
        lines[i] = "            exec_result = registry.execute(tool_name, kwargs)\n"
    if "if not exec_result.success:" in line:
        lines[i] = "            if not exec_result.success:\n"
    if "return AgentOutput(task_id=inputs.task_id, status=\"failed\"" in line and "exec_result.error" in line:
        lines[i] = "                return AgentOutput(task_id=inputs.task_id, status=\"failed\", result=\"\", error=exec_result.error)\n"
    if "tool_outputs_collected.append" in line and "exec_result.output" in line:
        lines[i] = "            tool_outputs_collected.append(f\"Tool `{tool_name}` output: {exec_result.output}\")\n"

with open('src/jarvis/agents/specialists.py', 'w') as f:
    f.writelines(lines)
