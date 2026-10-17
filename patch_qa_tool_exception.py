with open('src/jarvis/tools.py', 'r') as f:
    content = f.read()

def raise_unsafe(reason):
    raise Exception(f"Unsafe request detected: {reason}")

new_qa_tool = """def _validate_handler(is_safe, reason):
    if not is_safe:
        raise Exception(f"Unsafe request detected: {reason}")
    return f"Validation result: safe={is_safe}, reason={reason}"

# 4. QA Security Agent Tool
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
    _validate_handler
)"""

import re
content = re.sub(r'# 4\. QA Security Agent Tool.*', new_qa_tool, content, flags=re.DOTALL)

with open('src/jarvis/tools.py', 'w') as f:
    f.write(content)
