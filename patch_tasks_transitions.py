import re

with open('src/jarvis/tasks.py', 'r') as f:
    content = f.read()

# Fix the duplicate PLANNING transition block
content = content.replace("    TaskStatus.PLANNING: {TaskStatus.RUNNING, TaskStatus.WAITING_FOR_APPROVAL, TaskStatus.FAILED, TaskStatus.CANCELLED},\n    TaskStatus.PLANNING: {\n        TaskStatus.RUNNING,\n        TaskStatus.WAITING_FOR_APPROVAL,\n        TaskStatus.FAILED,\n        TaskStatus.CANCELLED,\n    },", "    TaskStatus.PLANNING: {\n        TaskStatus.RUNNING,\n        TaskStatus.WAITING_FOR_APPROVAL,\n        TaskStatus.FAILED,\n        TaskStatus.CANCELLED,\n    },")

with open('src/jarvis/tasks.py', 'w') as f:
    f.write(content)
