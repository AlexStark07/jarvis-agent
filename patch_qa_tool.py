import re

with open('src/jarvis/tools.py', 'r') as f:
    content = f.read()

new_qa_tool = """# 4. QA Security Agent Tool
registry.register(
    ToolConfig(
        name="validate_output",
        description="Validates output for safety and security.",
        input_schema={
            "type": "object",
            "properties": {
                "is_safe": {"type": "boolean"},
                "reason": {"type": "string"}
            },
            "required": ["is_safe", "reason"]
        }
    ),
    lambda is_safe, reason: f"Validation result: safe={is_safe}, reason={reason}" if is_safe else Exception(f"Unsafe request detected: {reason}")
)"""

content = re.sub(r'# 4\. QA Security Agent Tool.*?lambda is_safe, reason: f"Validation result: safe=\{is_safe\}, reason=\{reason\}"\n\)', new_qa_tool, content, flags=re.DOTALL)

with open('src/jarvis/tools.py', 'w') as f:
    f.write(content)
