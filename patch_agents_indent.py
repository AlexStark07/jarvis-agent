import re

with open('src/jarvis/agents/specialists.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.startswith("            exec_result = registry.execute(tool_name, kwargs)"):
        lines[i] = "                exec_result = registry.execute(tool_name, kwargs)\n"
    elif line.startswith("            if not exec_result.success:"):
        lines[i] = "                if not exec_result.success:\n"
    elif line.startswith("                return AgentOutput(task_id=inputs.task_id, status=\"failed\", result=\"\", error=exec_result.error)"):
        lines[i] = "                    return AgentOutput(task_id=inputs.task_id, status=\"failed\", result=\"\", error=exec_result.error)\n"
    elif line.startswith("            tool_outputs_collected.append(f\"Tool `{tool_name}` output: {exec_result.output}\")"):
        lines[i] = "                tool_outputs_collected.append(f\"Tool `{tool_name}` output: {exec_result.output}\")\n"

with open('src/jarvis/agents/specialists.py', 'w') as f:
    f.writelines(lines)
