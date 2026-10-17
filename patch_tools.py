import re

with open('src/jarvis/tools.py', 'r') as f:
    content = f.read()

new_method = """    def get_langchain_tools(self, tool_names: list[str]) -> list[Any]:
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

        return tools"""

content = content.replace("    def execute(self, name: str, kwargs: dict) -> ToolExecutionResult:", new_method + "\n\n    def execute(self, name: str, kwargs: dict) -> ToolExecutionResult:")

with open('src/jarvis/tools.py', 'w') as f:
    f.write(content)
