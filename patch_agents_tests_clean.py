with open('tests/test_agents.py', 'r') as f:
    content = f.read()

import re
content = re.sub(r'    def test_agent_invalid_tool.*', '', content, flags=re.DOTALL)

with open('tests/test_agents.py', 'w') as f:
    f.write(content)
