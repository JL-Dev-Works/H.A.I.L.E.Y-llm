

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



    # =========================================================

    # GENERATE RESPONSE AND EXECUTE TOOLS

    # =========================================================



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



            # No tool call: return normal response.

            if tool_request is None:



                response = self._clean_response(raw_response)



                if on_token:

                    on_token(response)



                return response



            tool_name = tool_request.get("tool")

            arguments = tool_request.get("arguments", {})



            if not isinstance(arguments, dict):

                arguments = {}



            normalized_name = self.tool_executor.normalize_tool_name(

                tool_name

            )



            # Maximum number of tool calls.

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

                        "Never claim an action succeeded if it did not."

                    ),

                })



                final_response = self._generate_raw(conversation)



                if self._parse_tool_request(final_response) is not None:



                    response = (

                        "Ik kan de gevraagde handeling niet verder uitvoeren."

                    )



                else:



                    response = self._clean_response(final_response)



                if on_token:

                    on_token(response)



                return response



            # Do not retry a failed tool.

            if normalized_name in failed_tools:



                result = {

                    "success": False,

                    "tool": normalized_name,

                    "error": "This tool already failed during this response.",

                    "error_type": "RepeatedFailedTool",

                }



                tool_call_count += 1



            else:



                print(

                    f"[HAILEY TOOL] Executing: {normalized_name}"

                )



                print(

                    f"[HAILEY TOOL] Arguments: {arguments}"

                )



                result = self.tool_executor.execute(

                    normalized_name,

                    arguments,

                )



                tool_call_count += 1



                if not isinstance(result, dict):

                    result = {

                        "success": False,

                        "tool": normalized_name,

                        "error": "Invalid tool result.",

                        "error_type": "InvalidToolResult",

                    }



                if result.get("success") is True:



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



            # Add the original tool request to the conversation.

            conversation.append({

                "role": "assistant",

                "content": raw_response,

            })



            # Return tool result to the model.

            if result.get("success") is True:



                tool_context = (

                    "INTERNAL TOOL RESULT\n"

                    "The tool executed successfully.\n"

                    "Use the returned information to answer the user's "

                    "original request.\n"

                    "Only report what the result confirms.\n\n"

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

                    "- Do not show technical errors to the user.\n"

                    "- Do not expose Python exceptions or stack traces.\n"

                    "- Explain briefly that the action failed.\n"

                    "- Never claim the action succeeded.\n"

                    "- Do not retry the failed tool.\n"

                    "- Be honest about the result."

                )



            conversation.append({

                "role": "user",

                "content": tool_context,

            })



    # =========================================================

    # TOOL INSTRUCTIONS

    # =========================================================



    def _add_tool_instructions(self, conversation):



        available_tools = self.tool_executor.get_available_tools()



        instructions = f"""

HAILEY TOOL SYSTEM



You are Hailey, a local AI assistant running on the user's computer.



You have access to tools through your Python tool executor.



AVAILABLE TOOLS:



{json.dumps(available_tools, ensure_ascii=False)}





GENERAL RULES:



\- Use tools when necessary to complete the user's request.

\- Never pretend to have executed a tool.

\- Never invent tool results.

\- Never claim an action succeeded before receiving a successful result.

\- Use the exact argument names required by each tool.

\- Only use relative paths for local files.





FILE READER:



You can read files from the configured local file directory.



FileList:



Use this tool to list files and folders.



Example:



{{

    "tool": "FileList",

    "arguments": {{

        "directory": ".",

        "recursive": false

    }}

}}





FileRead:



Use this tool to read a file.



Example:



{{

    "tool": "FileRead",

    "arguments": {{

        "path": "test.txt"

    }}

}}





FileInfo:



Use this tool to retrieve file information.



Example:



{{

    "tool": "FileInfo",

    "arguments": {{

        "path": "test.txt"

    }}

}}





ARCHIVING:



You have access to Hailey's file archiver.



The archiver works with files inside:



user/imports/



The path supplied to the archiver must be relative to the imports directory.



When the user explicitly asks to archive one specific file,

you MUST use ArchiveFile.



ArchiveFile:



The argument name MUST be "path".



Example:



{{

    "tool": "ArchiveFile",

    "arguments": {{

        "path": "test_document.txt"

    }}

}}



For files in subfolders:



{{

    "tool": "ArchiveFile",

    "arguments": {{

        "path": "subfolder/test_document.txt"

    }}

}}



ArchiveFile rules:



\- Always use ArchiveFile for a specific archive request.

\- Use "path", never "file_path".

\- Only use paths relative to user/imports/.

\- Never invent filenames.

\- Never claim success before receiving the tool result.

\- If success is true, confirm the file was archived.

\- If success is false, explain that archiving failed.





ArchiveAll:



Use when the user explicitly asks to archive all imported files.



Example:



{{

    "tool": "ArchiveAll",

    "arguments": {{}}

}}





ArchiveList:



Use when the user asks which files are in the archive.



Example:



{{

    "tool": "ArchiveList",

    "arguments": {{}}

}}





ArchiveStatistics:



Use when the user asks for archive statistics.



Example:



{{

    "tool": "ArchiveStatistics",

    "arguments": {{}}

}}





TOOL CALL FORMAT:



You may return a tool call in JSON format:



{{

    "tool": "ArchiveFile",

    "arguments": {{

        "path": "test_document.txt"

    }}

}}



You may also use the model's native tool-call format if supported.



When making a tool call, do not include an explanation around it.



After receiving the tool result, answer the user naturally.



Never claim a tool succeeded if its result reports failure.

"""



        if conversation and conversation[0].get("role") == "system":



            conversation.insert(

                1,

                {

                    "role": "system",

                    "content": instructions,

                }

            )



        else:



            conversation.insert(

                0,

                {

                    "role": "system",

                    "content": instructions,

                }

            )



    # =========================================================

    # RAW MODEL GENERATION

    # =========================================================



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



    # =========================================================

    # PARSE TOOL REQUEST

    # =========================================================



    def _parse_tool_request(self, response):
        """Extract JSON or native-format tool calls, including after thought text."""
        if not isinstance(response, str):
            return None

        content = response.strip()

        # The model may prepend <|channel>thought ... <channel|> before JSON.
        decoder = json.JSONDecoder()
        for match in re.finditer(r"\{", content):
            try:
                parsed, _ = decoder.raw_decode(content[match.start():])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                tool_name = parsed.get("tool")
                arguments = parsed.get("arguments", {})
                if isinstance(tool_name, str) and isinstance(arguments, dict):
                    return {"tool": tool_name, "arguments": arguments}

        patterns = (
            r"<\|tool_call>\s*call:([A-Za-z_][A-Za-z0-9_]*)\s*\{(.*?)\}\s*<tool_call\|>",
            r"<\|tool_call>\s*call:([A-Za-z_][A-Za-z0-9_]*)\s*\{(.*)\}",
        )
        for pattern in patterns:
            match = re.search(pattern, content, flags=re.DOTALL | re.IGNORECASE)
            if match:
                arguments = self._parse_native_arguments(match.group(2).strip())
                if arguments is not None:
                    return {"tool": match.group(1), "arguments": arguments}
        return None


    def _parse_native_arguments(self, raw_arguments):
        if not isinstance(raw_arguments, str):
            return None
        raw_arguments = raw_arguments.strip()
        if not raw_arguments:
            return {}

        cleaned = raw_arguments.replace('<|"|>', '"')
        arguments = {}
        parts = re.split(r",\s*(?=[A-Za-z_][A-Za-z0-9_]*\s*:)", cleaned)
        for part in parts:
            if ":" not in part:
                return None
            key, value = part.split(":", 1)
            key, value = key.strip(), value.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                return None
            value = re.sub(r"<\|.*?\|>", "", value).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            value = value.strip()
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.lower() == "null":
                value = None
            arguments[key] = value
        return arguments


    # =========================================================



    def _clean_response(self, response):
        if not isinstance(response, str):
            return ""
        response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL | re.IGNORECASE)
        response = re.sub(r"(?im)^Thinking:.*(?:\n|$)", "", response)
        response = re.sub(r"<\|tool_call>.*?<tool_call\|>", "", response, flags=re.DOTALL | re.IGNORECASE)
        response = re.sub(r"<tool_call>.*?</tool_call>", "", response, flags=re.DOTALL | re.IGNORECASE)
        return response.strip()


    # =========================================================



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



    # =========================================================

    # MEMORY ANALYSIS

    # =========================================================



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



1\. should_remember must be true or false.

2\. Use action "insert" for new information.

3\. Use action "update" when an existing memory should be updated.

4\. Use action "skip" when no memory should be saved.

5\. For updates, target_id MUST match an existing memory ID.

6\. For inserts, target_id must be null.

7\. Allowed categories:

   personal, preference, project, goal, fact, note.

8\. Importance must be an integer from 1 to 3.

9\. Key must be short and descriptive.

10\. Value must contain only information supported by the conversation.

11\. Never invent information.

12\. Do not save passwords, API keys, secrets or financial credentials.

13\. If nothing useful should be remembered, return:



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



    # =========================================================

    # AVAILABLE TOOLS

    # =========================================================



    def get_tool_names(self):



        return self.tool_executor.get_available_tools()
