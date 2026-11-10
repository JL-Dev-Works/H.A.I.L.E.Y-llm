## Welcome,
I only test the code on a windows pc, it should work on linux for the most part but I have not tested this yet. About macOS I have no idea.

All personal files are saved in the folder user.

Install everything from requirements.txt in a .venv

A .env file is needed with the following directory's
   - FILE_READER_DIRECTORY=
     - The location the file reader code can read files from.
   - MODEL_PATH=
     - The code expects a .gguf (for example gemma 4 e4b).

  - ARCHIVE_DIR=archive
  - IMPORT_DIR=imports
  - EXPORT_DIR=exports
  - METADATA_DIR=metadata
  - ARCHIVE_MAX_SIZE_MB=100
    - needed for the archiver tool, if not changed these will be the default directorys within the root folder.



Under the folder user/ in the root folder there will be a file needed called preference.py in here the user can set custom system prompts that will always be chosen first if conflicting with a original system prompt from config.py. when this file is missing or empty the llm will just juse the original system prompt. the preference.py file will need the following format.

 - USER_PREFERENCE = """
   
   Your custom prompt.

   """

Run main.py for the LLM to boot up.

---

This project is a work in progress. Expect bugs, unexpected behavior, and questionable architectural decisions.

---

## known problems
- The model used for testing is gemma 4 e4b, the problem is that most pretrained models have different outputs and the code is almost completely based around this model. So it is likely a   part of the tool code will have to be changed or some sort of translator code as a middle man will be needed for other models to work correctly.
- The loading icon displayed when the agent is doing something is off centered.
- The first message after starting the main code always takes a lot longer to generate.
- The gui needs a bit of work.



## Disclaimer

This software is provided "as is", without warranty of any kind.

Use it at your own risk. The author is not responsible for data loss, system damage, unexpected behavior, or other issues resulting from the use of this software.

Important: This AI agent can interact with files on your system. Make sure FILE_READER_DIRECTORY points only to a directory you are comfortable allowing it to access.


goodluck.
