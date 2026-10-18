import re

with open('src/jarvis/agents/specialists.py', 'r') as f:
    content = f.read()

# Already checks for cancellation per loop.
# Let's verify if `cancelled` enum is properly compared.
# Yes, current_task.status == "cancelled" will fail because task.status is an Enum.
content = content.replace("current_task.status == \"cancelled\"", "current_task.status.value == \"cancelled\"")

with open('src/jarvis/agents/specialists.py', 'w') as f:
    f.write(content)
