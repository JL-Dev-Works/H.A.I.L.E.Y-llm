
import os
from pathlib import Path
from dotenv import load_dotenv
from user.preference import USER_PREFERENCE



ROOT = Path(__file__).resolve().parent

load_dotenv(ROOT / ".env")


#---
#  Values that can be changed here. (other values can adjusted in the .env file acording to the README, most of those values are too sensitive to just leave here) 
#---

CORE_DIR = ROOT / "core"
TOOLS_DIR = ROOT / "tools"
MEMORY_DIR = ROOT / "memory"
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
USER_DIR = ROOT / "user"

#-----

FILE_READER_MAX_SIZE_MB = 10
FILE_READER_MAX_OUTPUT_CHARS = 30_000

#---

MEMORY_ENABLED = True
# Automatically recognize and save memories
MEMORY_AUTO_SAVE = True
# Minimum importance for automatic memories
MEMORY_MIN_IMPORTANCE = 2
# Maximum memories added to model context
MEMORY_MAX_CONTEXT_ITEMS = 10
# Maximum characters used by memory context
MEMORY_MAX_CONTEXT_CHARS = 3000
# SQLite database
MEMORY_DB_PATH = USER_DIR / "memory.db"
# Short-term conversation memory
SHORT_TERM_MAX_MESSAGES = 30

#---




def get_user_directory(env_name: str, default: str) -> Path:
    """
    Resolve a user directory and prevent access outside USER_DIR.
    Relative paths are resolved from USER_DIR.
    """

    raw_path = os.getenv(env_name, default)
    path = Path(raw_path).expanduser()

    if not path.is_absolute():
        path = USER_DIR / path

    path = path.resolve()
    user_root = USER_DIR.resolve()

    if not path.is_relative_to(user_root):
        raise ValueError(
            f"{env_name} must be located inside USER_DIR."
        )

    return path


ARCHIVE_DIR = get_user_directory(
    "ARCHIVE_DIR", "archive"
)

IMPORT_DIR = get_user_directory(
    "IMPORT_DIR", "imports"
)

EXPORT_DIR = get_user_directory(
    "EXPORT_DIR", "exports"
)

METADATA_DIR = get_user_directory(
    "METADATA_DIR", "metadata"
)

ARCHIVE_DATABASE = METADATA_DIR / "archive.json"


# Maximum archive file size
ARCHIVE_MAX_SIZE_MB = int(
    os.getenv("ARCHIVE_MAX_SIZE_MB", "100")
)


# Allowed file extensions
ARCHIVE_ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".pdf",
    ".doc", ".docx",
    ".xls", ".xlsx",
    ".ppt", ".pptx",
    ".csv", ".json", ".xml",
    ".yaml", ".yml", ".toml",
    ".ini", ".log",
    ".png", ".jpg", ".jpeg",
    ".gif", ".webp", ".bmp",
    ".svg", ".ico",
    ".py", ".js", ".ts",
    ".html", ".css",
    ".sql", ".sh",
    ".java", ".cpp", ".c",
    ".h", ".hpp", ".rs",
    ".go", ".php",
}


# Create user directories
for directory in (
    ARCHIVE_DIR,
    IMPORT_DIR,
    EXPORT_DIR,
    METADATA_DIR,
    ARCHIVE_DIR / "documents",
    ARCHIVE_DIR / "images",
    ARCHIVE_DIR / "code",
    ARCHIVE_DIR / "research",
    ARCHIVE_DIR / "uncategorized",
):
    directory.mkdir(parents=True, exist_ok=True)



# Create directories if they don't exist
for directory in (
    CORE_DIR,
    TOOLS_DIR,
    MEMORY_DIR,
    LOG_DIR,
    USER_DIR
):
    directory.mkdir(parents=True, exist_ok=True)




FILE_READER_DIRECTORY = Path(
    os.getenv(
        "FILE_READER_DIRECTORY",
        str(ROOT / "access folder")
    )
)



MODEL_PATH = Path(
    os.getenv(
        "MODEL_PATH",
        str(MODELS_DIR / "model.gguf")
    )
)

N_THREADS = 4
N_CTX = 8192
MAX_TOKENS = 2048



# Probeer gebruikersvoorkeuren te importeren
try:
    from user.preference import USER_PREFERENCE

    if not isinstance(USER_PREFERENCE, str):
        USER_PREFERENCE = ""

except (ImportError, AttributeError):
    USER_PREFERENCE = ""


SYSTEM_PROMPT = """
You are Hailey, a local AI assistant.

PERSONALITY:
- Be calm, natural and straightforward.
- Be friendly without being overly enthusiastic.
- Have a grounded, mature and slightly informal personality.
- Be confident when you know something.
- Be honest when you are uncertain.
- Do not act overly cheerful or overly apologetic.

WRITING STYLE:
- Never use emojis or emoticons.
- Avoid excessive exclamation marks.
- Do not use exaggerated expressions such as:
  "That's amazing!", "Absolutely!", or "I'm so excited!"
- Do not give unnecessary compliments.
- Do not repeat the user's question before answering.
- Avoid unnecessary introductions.
- Keep answers concise when the question is simple.
- Give detailed explanations when the subject requires them.
- Use natural language rather than generic AI phrases.

CONVERSATION:
- Do not end every response with a follow-up question.
- Only ask questions when additional information is actually needed.
- Do not constantly offer extra services or suggestions.
- Respond naturally to casual conversation.
- Remember relevant context from previous messages.

IDENTITY:
- Your name is Hailey.
- You are a local AI assistant running on the user's computer.
- Never pretend to be a different AI or claim to be developed by another company.
- Be transparent about your capabilities and limitations.

Your goal is to be a capable, reliable assistant that feels natural to talk to.
You do not need to impress the user. Just be useful.
"""


# Combineer de originele prompt met gebruikersvoorkeuren
FINAL_SYSTEM_PROMPT = SYSTEM_PROMPT

if USER_PREFERENCE.strip():
    FINAL_SYSTEM_PROMPT += f"""

USER PREFERENCES (HIGHER PRIORITY):
The following instructions come directly from the user.
They override any conflicting instructions in the default system prompt.

{USER_PREFERENCE}
"""