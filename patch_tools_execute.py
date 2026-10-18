import re

with open('src/jarvis/tools.py', 'r') as f:
    content = f.read()

# Execute command needs workspace but only takes command and worker_manager from kwargs.
# Add workspace fallback.
new_execute = """    lambda command, worker_manager: worker_manager.execute(command, os.path.abspath(os.environ.get("JARVIS_WORKSPACE", "/tmp/jarvis_workspace")))"""

content = re.sub(r'    lambda command, worker_manager, workspace: worker_manager\.execute\(command, workspace\)', new_execute, content)

with open('src/jarvis/tools.py', 'w') as f:
    f.write(content)
