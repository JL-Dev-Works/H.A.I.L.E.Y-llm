from tools.tool_executor import ToolExecutor

executor = ToolExecutor()

result = executor.execute(
    "ArchiveFile",
    {
        "path": "test_document.txt"
    }
)

print("\nARCHIVE RESULT:")
print(result)