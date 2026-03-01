from datetime import datetime
from enum import StrEnum

from .env_vars import LOG_FILE, DEBUG_LEVEL

class LOG_LEVEL(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    ERROR = "ERROR"

def fmt_time() -> str:
    return datetime.now().strftime("%I:%M %p").lstrip("0") 

def log_event(msg: str, type: str) -> None:
    if type.casefold().replace(" ", "") == DEBUG_LEVEL.casefold().replace(" ", ""):
        line: str = f"{fmt_time()} — {msg}"
        with open(LOG_FILE, "a", encoding="utf-8") as f: 
            f.write(line + "\n")
        print(f"[LOG] {line}")