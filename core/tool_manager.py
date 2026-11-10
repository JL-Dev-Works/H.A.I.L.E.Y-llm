
from typing import Callable, Any


class ToolManager:

    def __init__(self):
        self.tools: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        function: Callable,
        description: str,
    ) -> None:

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Toolnaam mag niet leeg zijn.")

        if name in self.tools:
            raise ValueError(f"Tool already registered: {name}")

        if not callable(function):
            raise TypeError("Tool function must be callable.")

        self.tools[name] = {
            "function": function,
            "description": description,
        }


    def execute(self, name: str, **kwargs) -> Any:

        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")

        if not isinstance(kwargs, dict):
            raise TypeError("Tool arguments must be a dictionary.")

        tool = self.tools[name]

        return tool["function"](**kwargs)

 
    def list_tools(self) -> dict:

        return {
            name: {
                "description": tool["description"],
            }
            for name, tool in self.tools.items()
        }


    def get_tool_descriptions(self) -> dict[str, str]:

        return {
            name: tool["description"]
            for name, tool in self.tools.items()
        }

    def has_tool(self, name: str) -> bool:

        return name in self.tools
