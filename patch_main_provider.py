import re

with open('src/jarvis/api/main.py', 'r') as f:
    content = f.read()

content = content.replace("db_path = \"data/jarvis.db\"", "db_path = \"data/jarvis.db\"\nprovider = get_provider(\"mock\")")

with open('src/jarvis/api/main.py', 'w') as f:
    f.write(content)
