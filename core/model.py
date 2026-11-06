
import json
import re

from llama_cpp import Llama

from config import (
    MODEL_PATH,
    N_CTX,
    N_THREADS,
    MAX_TOKENS,
)

from tools.tool_executor import ToolExecutor


class HaileyModel:

    def __init__(self, tool_executor=None):

        print("[HAILEY] Loading model...")

        self.model = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_gpu_layers=0,
            verbose=False,
        )

        self.tool_executor = tool_executor or ToolExecutor()

        self.max_tool_calls = 3

        print("[HAILEY] Model loaded.")
        print("[HAILEY] Tool executor initialized.")



    def generate(self, messages, on_token=None):

        conversation = [
            message.copy()
            for message in messages
        ]

        self._add_tool_instructions(conversation)

        failed_tools = set()
        tool_call_count = 0

        while True:

            raw_response = self._generate_raw(conversation)

            tool_request = self._parse_tool_request(raw_response)

       
            if tool_request is None:

                response = self._clean_response(raw_response)

                if on_token:
                    on_token(response)

                return response

            tool_name = tool_request.get("tool")
            arguments = tool_request.get("arguments", {})

            if not isinstance(arguments, dict):
                arguments = {}

            normalized_name = (
                self.tool_executor.normalize_tool_name(tool_name)
            )

          
            if tool_call_count >= self.max_tool_calls:

                conversation.append({
                    "role": "assistant",
                    "content": raw_response,
                })

                conversation.append({
                    "role": "user",
                    "content": (
                        "You have reached the maximum number of tool calls. "
                        "Do not call any more tools. Answer the original "
                        "request using the information already available. "
                        "If something could not be completed, explain this "
                        "briefly and naturally. Never claim an action "
                        "succeeded if it did not."
                    ),
                })

                final_response = self._generate_raw(conversation)

                response = self._clean_response(final_response)

        
                if self._parse_tool_request(final_response) is not None:
                    response = (
                        "Ik heb mijn beschikbare acties geprobeerd, maar "
                        "kan de gevraagde handeling niet verder uitvoeren. "
                        "Ik kan je wel verder helpen met de informatie "
                        "die ik al heb."
                    )

                if on_token:
                    on_token(response)

                return response

  
            if normalized_name in failed_tools:

                result = {
                    "success": False,
                    "tool": normalized_name,
                    "error": (
                        "This tool already failed during the current "
                        "response. Do not retry it."
                    ),
                    "error_type": "RepeatedFailedTool",
                }

                tool_call_count += 1

            else:

                print(
                    f"[HAILEY TOOL] Executing: {normalized_name}"
                )

                result = self.tool_executor.execute(
                    normalized_name,
                    arguments,
                )

                tool_call_count += 1

                if result.get("success"):

                    print(
                        f"[HAILEY TOOL] {normalized_name} completed."
                    )

                else:

                    print(
                        f"[HAILEY TOOL ERROR] "
                        f"{normalized_name}: "
                        f"{result.get('error_type', 'ToolError')}"
                    )

                    failed_tools.add(normalized_name)


            conversation.append({
                "role": "assistant",
                "content": raw_response,
            })

  
            if result.get("success"):

                tool_context = (
                    "INTERNAL TOOL RESULT\n"
                    "The tool executed successfully.\n"
                    "Use the returned information to answer the user's "
                    "original request.\n\n"
                    + self._serialize_result(result)
                )

            else:

                tool_context = (
                    "INTERNAL TOOL FAILURE\n"
                    "The requested tool did not execute successfully.\n\n"
                    "Technical error information:\n"
                    + self._serialize_result(result)
                    + "\n\n"
                    "IMPORTANT INSTRUCTIONS:\n"
                    "- Do not show technical error messages to the user.\n"
                    "- Do not expose Python exceptions or stack traces.\n"
                    "- Briefly explain that the action could not be completed.\n"
                    "- Do not claim that the action succeeded.\n"
                    "- Do not retry this failed tool during this response.\n"
                    "- Continue helping with the original request.\n"
                    "- Use any information already available.\n"
                    "- Be honest if the request cannot be completed."
                )

            conversation.append({
                "role": "user",
                "content": tool_context,
            })



 
    def _add_tool_instructions(self, conversation):

        available_tools = self.tool_executor.get_available_tools()

        instructions = f"""
HAILEY TOOL SYSTEM

You are Hailey, a local AI assistant running on the user's computer.

You HAVE access to tools through your Python tool executor.

AVAILABLE TOOLS:
{json.dumps(available_tools, ensure_ascii=False)}

FILE READER:

You have a File Reader tool that can read files from the
user-configured directory on the local computer.

You MUST use these tools when the user asks about files.

FileList:
Use this to list files and folders.

Example:
{{
    "tool": "FileList",
    "arguments": {{
        "directory": ".",
        "recursive": false
    }}
}}

FileRead:
Use this to read a file.

Example:
{{
    "tool": "FileRead",
    "arguments": {{
        "path": "test.txt"
    }}
}}

FileInfo:
Use this to retrieve file information.

Example:
{{
    "tool": "FileInfo",
    "arguments": {{
        "path": "test.txt"
    }}
}}

IMPORTANT:
- Do not claim you cannot access the local filesystem.
- You can access files through FileList, FileRead and FileInfo.
- Never invent file contents.
- Always read a file before answering questions about its contents.
- Only use relative paths.
- Never attempt to access files outside the configured directory.
- If a tool fails, explain that honestly.
- Never claim a tool succeeded if it failed.

TOOL CALL FORMAT:

When calling a tool, return ONLY valid JSON:

{{
    "tool": "ToolName",
    "arguments": {{}}
}}

Do not include explanations around a tool call.
"""

        if conversation and conversation[0].get("role") == "system":

            conversation.insert(
                1,
                {
                    "role": "system",
                    "content": instructions
                }
            )

        else:

            conversation.insert(
                0,
                {
                    "role": "system",
                    "content": instructions
                }
            )



    def _generate_raw(self, messages):

        response = self.model.create_chat_completion(
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.7,
            stream=False,
        )

        try:

            return (
                response["choices"][0]["message"]["content"] or ""
            )

        except (KeyError, IndexError, TypeError):

            return ""



    def _parse_tool_request(self, response):

        if not isinstance(response, str):
            return None

        content = response.strip()

       
        match = re.search(
            r"<tool_call>\s*(.*?)\s*</tool_call>",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )

        if match:
            content = match.group(1).strip()


        content = re.sub(
            r"^```(?:json)?\s*",
            "",
            content,
            flags=re.IGNORECASE,
        )

        content = re.sub(
            r"\s*```$",
            "",
            content,
        )

        try:

            parsed = json.loads(content)

        except json.JSONDecodeError:

            return None

        if not isinstance(parsed, dict):
            return None

        tool_name = parsed.get("tool")

        if not isinstance(tool_name, str):
            return None

        arguments = parsed.get("arguments", {})

        if not isinstance(arguments, dict):
            return None

        return {
            "tool": tool_name,
            "arguments": arguments,
        }



    def _clean_response(self, response):

        if not isinstance(response, str):
            return ""

   
        response = re.sub(
            r"<think>.*?</think>",
            "",
            response,
            flags=re.DOTALL | re.IGNORECASE,
        )


        response = re.sub(
            r"(?im)^Thinking:.*(?:\n|$)",
            "",
            response,
        )


        response = re.sub(
            r"<tool_call>.*?</tool_call>",
            "",
            response,
            flags=re.DOTALL | re.IGNORECASE,
        )

        return response.strip()



    def _serialize_result(self, result):

        try:

            return json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        except Exception:

            return str(result)



    def analyze_memory(
        self,
        message=None,
        user_message=None,
        conversation_history=None,
        existing_memories=None,
        **kwargs
    ):

    
        if message is None:
            message = user_message

        if not message:
            return "{}"

        conversation_history = conversation_history or []
        existing_memories = existing_memories or []

        prompt = [
            {
                "role": "system",
                "content": """
You are Hailey's memory classification system.

Analyze the latest user message and determine whether
useful information should be remembered.

Return ONLY valid JSON using this exact structure:

{
    "should_remember": true,
    "action": "insert",
    "target_id": null,
    "category": "project",
    "key": "short_identifier",
    "value": "information to remember",
    "importance": 3
}

RULES:

1. should_remember must be true or false.
2. Use action "insert" for new information.
3. Use action "update" when an existing memory should be updated.
4. Use action "skip" when no memory should be saved.
5. For updates, target_id MUST match an existing memory ID.
6. For inserts, target_id must be null.
7. Allowed categories:
   personal, preference, project, goal, fact, note.
8. Importance must be an integer from 1 to 3.
9. Key must be short and descriptive.
10. Value must contain only information supported by the conversation.
11. Never invent information.
12. Do not save passwords, API keys, secrets or financial credentials.
13. If nothing useful should be remembered, return:

{
    "should_remember": false,
    "action": "skip",
    "target_id": null,
    "category": "note",
    "key": "",
    "value": "",
    "importance": 1
}

Return JSON only. No Markdown or explanations.
"""
            },
            {
                "role": "user",
                "content": (
                    "LATEST USER MESSAGE:\n"
                    + str(message)
                    + "\n\nCONVERSATION HISTORY:\n"
                    + json.dumps(
                        conversation_history,
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\n\nEXISTING MEMORIES:\n"
                    + json.dumps(
                        existing_memories,
                        ensure_ascii=False,
                        default=str,
                    )
                ),
            },
        ]

        try:

            response = self.model.create_chat_completion(
                messages=prompt,
                max_tokens=350,
                temperature=0.1,
                stream=False,
            )

            content = (
                response["choices"][0]["message"]["content"] or "{}"
            )

            return content.strip()

        except Exception as error:

            print(
                "[HAILEY MEMORY WARNING] "
                f"{type(error).__name__}: {error}"
            )

            return "{}"



    def get_tool_names(self):

        return self.tool_executor.get_available_tools()
