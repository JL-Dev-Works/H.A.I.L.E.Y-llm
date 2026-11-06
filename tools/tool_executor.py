
import inspect

from pathlib import Path

import config

from tools.internet_access.web_search import WebResearchTool
from tools.file_reader import FileReaderTool
from core.memory_manager import MemoryManager


class ToolExecutor:

    def __init__(self, memory_manager=None):

        self.web = WebResearchTool()
        self.memory = memory_manager or MemoryManager()



        directory = getattr(
            config,
            "FILE_READER_DIRECTORY",
            None,
        )

        if directory is None:
            raise RuntimeError(
                "FILE_READER_DIRECTORY ontbreekt in config.py."
            )

        self.file_reader = FileReaderTool(
            allowed_directory=directory,
            max_file_size_mb=getattr(
                config,
                "FILE_READER_MAX_SIZE_MB",
                10,
            ),
            max_output_chars=getattr(
                config,
                "FILE_READER_MAX_OUTPUT_CHARS",
                30000,
            ),
        )



        self.tools = {

            # Internet
            "WebSearch": self.web.search,
            "WebPageReader": self.web.read_page,
            "WebResearch": self.web.research,
            "WebContextFormatter": self.web.format_for_prompt,

            # Memory
            "Remember": self.memory.remember,
            "GetMemories": self.memory.get_memories,
            "GetMemoryContext": self.memory.get_context,
            "ForgetMemory": self.memory.forget,
            "ClearMemories": self.memory.clear,

            # File Reader
            "FileRead": self.file_reader.read_file,
            "FileList": self.file_reader.list_files,
            "FileInfo": self.file_reader.get_file_info,
        }



        self.aliases = {

            # Internet
            "websearch": "WebSearch",
            "web_search": "WebSearch",

            "webpagereader": "WebPageReader",
            "web_page_reader": "WebPageReader",

            "webresearch": "WebResearch",
            "web_research": "WebResearch",
            "webreasarch": "WebResearch",
            "webreseach": "WebResearch",
            "webresarch": "WebResearch",

            "webcontextformatter": "WebContextFormatter",
            "web_context_formatter": "WebContextFormatter",

            # Memory
            "remember": "Remember",

            "getmemories": "GetMemories",
            "get_memories": "GetMemories",

            "getmemorycontext": "GetMemoryContext",
            "get_memory_context": "GetMemoryContext",

            "forgetmemory": "ForgetMemory",
            "forget_memory": "ForgetMemory",

            "clearmemories": "ClearMemories",
            "clear_memories": "ClearMemories",

            # File Reader
            "fileread": "FileRead",
            "file_read": "FileRead",
            "readfile": "FileRead",
            "read_file": "FileRead",

            "filelist": "FileList",
            "file_list": "FileList",
            "listfiles": "FileList",
            "list_files": "FileList",

            "fileinfo": "FileInfo",
            "file_info": "FileInfo",
            "getfileinfo": "FileInfo",
            "get_file_info": "FileInfo",
        }



    def normalize_tool_name(self, tool_name):

        if not isinstance(tool_name, str):
            return None

        normalized = tool_name.strip().lower()

        return self.aliases.get(
            normalized,
            tool_name.strip(),
        )



    def execute(self, tool_name, arguments=None):

        """
        Voert een tool uit en geeft altijd een gestructureerd
        resultaat terug.
        """

        tool_name = self.normalize_tool_name(tool_name)

        if arguments is None:
            arguments = {}

        if not isinstance(arguments, dict):
            return {
                "success": False,
                "tool": tool_name,
                "error": "Tool arguments must be a dictionary.",
                "error_type": "InvalidArguments",
            }

        if tool_name is None:
            return {
                "success": False,
                "error": "Invalid tool name.",
                "error_type": "InvalidToolName",
            }

        tool = self.tools.get(tool_name)

        if tool is None:
            return {
                "success": False,
                "tool": tool_name,
                "error": f"Unknown tool: {tool_name}",
                "error_type": "UnknownTool",
                "available_tools": self.get_available_tools(),
            }

        # Alle herinneringen verwijderen vereist
        # expliciete bevestiging op applicatieniveau.
        if tool_name == "ClearMemories":
            return {
                "success": False,
                "tool": tool_name,
                "error": (
                    "Deleting all memories is blocked. "
                    "Explicit application-level confirmation is required."
                ),
                "error_type": "ConfirmationRequired",
            }

        try:

            signature = inspect.signature(tool)

            signature.bind(**arguments)

            result = tool(**arguments)

            return {
                "success": True,
                "tool": tool_name,
                "result": result,
            }

        except TypeError as error:

            return {
                "success": False,
                "tool": tool_name,
                "error": str(error),
                "error_type": "InvalidArguments",
            }

        except Exception as error:

            return {
                "success": False,
                "tool": tool_name,
                "error": str(error),
                "error_type": type(error).__name__,
            }



    def get_available_tools(self):

        return list(self.tools.keys())
