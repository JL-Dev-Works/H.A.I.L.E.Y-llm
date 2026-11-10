## Welcome,

- Yes it has many problems.
- No i don't have proper documentation.
- I'm pretty sure even god doesn't know what is going on here.
- The code itself is a mess of Dutch and English.

Anyway,

I only test the code on a windows pc, it should work on linux for the most part but I have not tested this yet. About macOS I have no idea.

All personal files are saved in the folder user.

Install everything from requirements.txt in a .venv

A .env file is needed with the following directory's
   - FILE_READER_DIRECTORY=
     - The location the file reader code can read files from.
   - MODEL_PATH=
     - The code expects a .gguf (for example gemma 4 e4b).

Run main.py for the LLM to boot up.

---

This project is a work in progress. Expect bugs, unexpected behavior, and questionable architectural decisions.

---

## Disclaimer

This software is provided "as is", without warranty of any kind.

Use it at your own risk. The author is not responsible for data loss, system damage, unexpected behavior, or other issues resulting from the use of this software.

Important: This AI agent can interact with files on your system. Make sure FILE_READER_DIRECTORY points only to a directory you are comfortable allowing it to access.


goodluck.
