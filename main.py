import uuid

from core.model import HaileyModel
from core.conversation import Conversation
from core.memory_manager import MemoryManager
from tools.tool_loader import ToolDocumentation
from tools.tool_loader import ToolDocumentation

from tools.internet_access.web_intent import should_search
from tools.internet_access.web_search import WebResearchTool, WebSearchError

from gui.app import run

if __name__ == "__main__":
    run()


def handle_command(message, memory):

    command, _, argument = message.partition(" ")

    command = command.lower()
    argument = argument.strip()

    if command == "/help":

        print("""
Available commands:

/memory             Show all memories
/memory TEXT        Save a manual memory
/forget ID          Delete a memory
/clear              Clear all memories
/exit               Exit Hailey
""")

        return True

    if command == "/memory" and not argument:

        memories = memory.get_memories()

        if not memories:
            print("No memories found.")

        else:

            print("\n--- Hailey Memory ---")

            for item in memories:

                print(
                    f"[{item['id']}] "
                    f"{item['category']}: "
                    f"{item['key']} = "
                    f"{item['value']}"
                )

            print()

        return True

    if command == "/memory" and argument:

        memory.remember(
            category="note",
            key=str(uuid.uuid4()),
            value=argument,
            importance=3,
            source="manual"
        )

        print("Memory saved.")
        return True

    if command == "/forget":

        try:

            memory_id = int(argument)

            if memory.forget(memory_id):
                print("Memory deleted.")

            else:
                print("Memory not found.")

        except ValueError:

            print("Usage: /forget ID")

        return True

    if command == "/clear":

        if argument.lower() != "confirm":

            print("This will delete all memories.")
            print("Type /clear confirm to continue.")

            return True

        memory.clear()

        print("All memories cleared.")
        return True

    return False


def main():

    print("Starting Hailey...")


    tool_docs = ToolDocumentation()

    web_tool = WebResearchTool()

    model = HaileyModel()
    conversation = Conversation()
    memory = MemoryManager()

    print("\nHailey is ready.")
    print("Type /help for commands.\n")

    while True:

        try:
            message = input("You: ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nHailey shutting down.")
            break

        if not message:
            continue

        if message.lower() == "/exit":
            print("Hailey shutting down.")
            break

        if message.startswith("/"):

            handled = handle_command(message, memory)

            if handled:
                continue


        conversation.add_user(message)


        try:

            memory_saved = memory.observe_user_message(
                message=message,
                model=model,
                conversation_history=conversation.get_history()
            )

            print(f"[MEMORY DEBUG] Saved or updated: {memory_saved}")

            if memory_saved:
                print("[Hailey memory: information stored]")

        except Exception as error:

            print(f"Memory warning: {error}")


        try:

            memory_context = memory.get_context()

        except Exception as error:

            print(f"Memory retrieval warning: {error}")
            memory_context = ""


        web_context = ""

        if should_search(message):

            print("\n[Hailey is searching the web...]")

            try:

                research = web_tool.research(
                    message,
                    max_results=3,
                    pages_to_read=1
                )

                web_context = web_tool.format_for_prompt(research)

                print(f"[WEB SEARCH] Found {len(research['sources'])} results.")

                for index, source in enumerate(research["sources"], start=1):
                    print(f"[{index}] {source['title']} - {source['url']}")

            except WebSearchError as error:

                print(f"[WEB SEARCH WARNING] {error}")

            except Exception as error:

                print(f"[WEB SEARCH WARNING] Unexpected error: {error}")


        messages = conversation.get_messages(
            memory_context=memory_context,
            extra_context=web_context,
            tool_context=tool_docs.get_documentation()
        )


        try:

            print("\nHailey: ", end="", flush=True)

            response = model.generate(messages)

            conversation.add_assistant(response)

            print("\n")

        except Exception as error:

            print(f"Generation error: {error}")

            if conversation.messages and conversation.messages[-1].get("role") == "user":
                conversation.messages.pop()


if __name__ == "__main__":
    main()
