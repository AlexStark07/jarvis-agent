import re

with open('src/jarvis/tools.py', 'r') as f:
    content = f.read()

# Fix execute method signature which didn't have kwargs correctly defined when updated
new_execute = """    def execute(self, name: str, kwargs: dict) -> ToolExecutionResult:
        if name not in self._handlers:
            return ToolExecutionResult(success=False, output="", error=f"Tool {name} not found.")

        try:
            # Pydantic validation mapping would normally occur here dynamically based on input_schema
            result = self._handlers[name](**kwargs)
            return ToolExecutionResult(success=True, output=str(result))
        except Exception as e:
            return ToolExecutionResult(success=False, output="", error=str(e))"""

content = re.sub(r'    def execute\(self, name: str, kwargs: dict\) -> ToolExecutionResult:.*?return ToolExecutionResult\(success=False, output="", error=str\(e\)\)', new_execute, content, flags=re.DOTALL)

with open('src/jarvis/tools.py', 'w') as f:
    f.write(content)

with open('src/jarvis/agents/specialists.py', 'r') as f:
    spec_content = f.read()

# Fix how registry.execute is called
spec_content = spec_content.replace(
    "exec_result = registry.execute(tool_name, tool_args, context_kwargs)",
    "kwargs = {**tool_args, **context_kwargs}\n            exec_result = registry.execute(tool_name, kwargs)"
)

with open('src/jarvis/agents/specialists.py', 'w') as f:
    f.write(spec_content)
