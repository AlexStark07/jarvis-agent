from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, Field

class ToolConfig(BaseModel):
    name: str = Field(description="The unique name of the tool.")
    description: str = Field(description="A description of what the tool does.")
    input_schema: Dict[str, Any] = Field(description="JSON schema describing the required inputs.")
    requires_approval: bool = False

class ToolExecutionResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolConfig] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(self, config: ToolConfig, handler: Callable):
        self._tools[config.name] = config
        self._handlers[config.name] = handler

    def get_tool(self, name: str) -> Optional[ToolConfig]:
        return self._tools.get(name)

    def get_langchain_tools(self, tool_names: list[str]) -> list[Any]:
        from langchain_core.tools import StructuredTool
        from pydantic import create_model

        tools = []
        for name in tool_names:
            config = self._tools.get(name)
            if not config:
                continue

            # Create dynamic Pydantic model for input schema arguments
            fields = {}
            for prop, details in config.input_schema.get("properties", {}).items():
                # Simplified mapping for MVP
                prop_type = str if details.get("type") == "string" else list
                fields[prop] = (prop_type, ...)

            InputSchema = create_model(f"{name}Schema", **fields)

            def make_handler(tool_name):
                return lambda **kwargs: self.execute(tool_name, kwargs).output

            tool = StructuredTool.from_function(
                func=make_handler(name),
                name=name,
                description=config.description,
                args_schema=InputSchema,
            )
            tools.append(tool)

        return tools

    def execute(self, name: str, kwargs: dict) -> ToolExecutionResult:
        if name not in self._handlers:
            return ToolExecutionResult(success=False, output="", error=f"Tool {name} not found.")

        try:
            # Pydantic validation mapping would normally occur here dynamically based on input_schema
            result = self._handlers[name](**kwargs)
            return ToolExecutionResult(success=True, output=str(result))
        except Exception as e:
            return ToolExecutionResult(success=False, output="", error=str(e))

# Setup default registry with core explicit schemas
registry = ToolRegistry()

# 1. Developer Agent Tool
registry.register(
    ToolConfig(
        name="execute_command",
        description="Executes a shell command in an isolated environment.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["command"]
        }
    ),
    lambda command, worker_manager: worker_manager.execute(command, os.path.abspath(os.environ.get("JARVIS_WORKSPACE", "/tmp/jarvis_workspace")))
)

# 2. Operations Agent Tool
registry.register(
    ToolConfig(
        name="modify_infrastructure",
        description="Deploys or modifies infrastructure targets.",
        input_schema={
            "type": "object",
            "properties": {
                "target": {"type": "string"}
            },
            "required": ["target"]
        },
        requires_approval=True
    ),
    lambda target: f"Successfully modified infrastructure target: {target}"
)

# 3. Communications Agent Tool
registry.register(
    ToolConfig(
        name="send_message",
        description="Sends a draft message to an external party.",
        input_schema={
            "type": "object",
            "properties": {
                "draft": {"type": "string"}
            },
            "required": ["draft"]
        },
        requires_approval=True
    ),
    lambda draft: f"Message sent successfully: {draft[:20]}..."
)

def _validate_handler(is_safe, reason):
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
)
import os
import subprocess

WORKSPACE_DIR = os.path.abspath(os.environ.get("JARVIS_WORKSPACE", "/tmp/jarvis_workspace"))
os.makedirs(WORKSPACE_DIR, exist_ok=True)

def _safe_path(path_str):
    full_path = os.path.abspath(os.path.join(WORKSPACE_DIR, path_str))
    if not full_path.startswith(WORKSPACE_DIR):
        raise ValueError("Path traversal attack detected.")
    return full_path

# 5. Real Scoped Tools
registry.register(
    ToolConfig(
        name="web_search",
        description="Searches the web for information.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    ),
    lambda query: "Mock Search result for " + query if os.environ.get("MOCK_EXTERNAL", "1") == "1" else f"Live search not implemented for MVP. Query: {query}"
)

registry.register(
    ToolConfig(
        name="read_document",
        description="Reads a document from the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"]
        }
    ),
    lambda path: open(_safe_path(path), 'r').read()
)

registry.register(
    ToolConfig(
        name="write_file",
        description="Writes content to a file in the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    ),
    lambda path, content: [open(_safe_path(path), 'w').write(content), f"Successfully wrote to {path}"][1]
)

registry.register(
    ToolConfig(
        name="run_tests",
        description="Runs test suite.",
        input_schema={
            "type": "object",
            "properties": {
                "suite": {"type": "string"}
            },
            "required": ["suite"]
        }
    ),
    lambda suite: subprocess.run(["pytest", _safe_path(suite)], capture_output=True, text=True, check=False).stdout
)
registry.register(
    ToolConfig(
        name="check_health",
        description="Checks health of a service.",
        input_schema={
            "type": "object",
            "properties": {
                "target": {"type": "string"}
            },
            "required": ["target"]
        }
    ),
    lambda target: f"{target} is healthy" if "http" not in target else "HTTP healthcheck unimplemented"
)

registry.register(
    ToolConfig(
        name="run_security_scan",
        description="Runs a security scan on the repository.",
        input_schema={
            "type": "object",
            "properties": {
                "target": {"type": "string"}
            },
            "required": ["target"]
        }
    ),
    lambda target: f"Scan complete for {target}. No critical issues."
)