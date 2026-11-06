
from pathlib import Path


class ToolDocumentation:

    def __init__(self):

        self.file_path = (
            Path(__file__).resolve().parent.parent
            / "core"
            / "tool_list.md"
        )

        self.documentation = ""

        self.reload()

    def reload(self):

        try:

            self.documentation = self.file_path.read_text(
                encoding="utf-8"
            )

        except FileNotFoundError:

            print("[TOOL WARNING] core/tool_list.md not found.")

            self.documentation = ""

        return self.documentation

    def get_documentation(self):

        return self.documentation
