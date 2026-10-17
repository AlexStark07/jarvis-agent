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
    lambda command, worker_manager, workspace: worker_manager.execute(command, workspace)
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
