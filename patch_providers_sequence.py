with open('src/jarvis/providers.py', 'r') as f:
    content = f.read()

import re
content = re.sub(
    r'        self.sequence = sequence or \[\]',
    r'        self.sequence = sequence if sequence is not None else _MOCK_SEQUENCE',
    content
)

with open('src/jarvis/providers.py', 'w') as f:
    f.write(content)
