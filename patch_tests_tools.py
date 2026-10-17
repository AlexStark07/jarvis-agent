import re

with open('tests/test_agents.py', 'r') as f:
    content = f.read()

# Update test_agents to use proper tools instead of direct strings
content = content.replace(
    'AIMessage(content="Mock Research Finding")',
    'AIMessage(content="", tool_calls=[ToolCall(name="web_search", args={"query": "Research test"}, id="call_1")]), AIMessage(content="Mock Research Finding")'
)

content = content.replace(
    'AIMessage(content="Code Changes completed.")',
    'AIMessage(content="", tool_calls=[ToolCall(name="write_file", args={"path": "test.py", "content": "Code"}, id="call_1")]), AIMessage(content="Code Changes completed.")'
)

with open('tests/test_agents.py', 'w') as f:
    f.write(content)


with open('tests/test_workflow.py', 'r') as f:
    content = f.read()

# Update test_workflow to use proper tool calls
content = content.replace(
    'AIMessage(content="Mock Research Finding"),',
    'AIMessage(content="", tool_calls=[ToolCall(name="web_search", args={"query": "search for information"}, id="call_1")]),\n            AIMessage(content="Mock Research Finding"),'
)

with open('tests/test_workflow.py', 'w') as f:
    f.write(content)
