with open('tests/test_workflow.py', 'r') as f:
    content = f.read()

import re
content = content.replace("jarvis.providers._MOCK_SEQUENCE.clear()", "jarvis.providers._MOCK_SEQUENCE.clear()\n        from jarvis.api.main import provider\n        provider.call_count = 0")

with open('tests/test_workflow.py', 'w') as f:
    f.write(content)

with open('tests/test_api.py', 'r') as f:
    content = f.read()

content = content.replace("jarvis.providers._MOCK_SEQUENCE.clear()", "jarvis.providers._MOCK_SEQUENCE.clear()\n        from jarvis.api.main import provider\n        provider.call_count = 0")

with open('tests/test_api.py', 'w') as f:
    f.write(content)
