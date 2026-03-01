import os
from dotenv import load_dotenv

load_dotenv()

CAMERA_INDEX: int = int(os.getenv("CAMERA_INDEX", "-1"))
if CAMERA_INDEX == -1:
    raise RuntimeError("CAMERA_INDEX not set")

LOG_FILE: str = os.getenv("LOG_FILE","")
if LOG_FILE == "":
    raise RuntimeError("LOG_FILE not set")

DEBUG_LEVEL: str = os.getenv("DEBUG_LEVEL","")
if DEBUG_LEVEL == "":
    raise RuntimeError("DEBUG_LEVEL not set")

DB_FILE: str = os.getenv("DB_FILE","")
if DB_FILE == "":
    raise RuntimeError("DB_FILE not set")

META_FILE: str = os.getenv("META_FILE","")
if META_FILE == "":
    raise RuntimeError("META_FILE not set")

SMALLTALK_LOG_URL: str = os.getenv("SMALLTALK_LOG_URL", "")
if SMALLTALK_LOG_URL == "":
    raise RuntimeError("SMALLTALK_LOG_URL not set")

SMALLTALK_LOG_TIMEOUT: int = int(os.getenv("SMALLTALK_LOG_TIMEOUT", "-1"))
if SMALLTALK_LOG_TIMEOUT == -1:
    raise RuntimeError("SMALLTALK_LOG_TIMEOUT not set")

GAZE_THRESHOLD: float = float(os.getenv("GAZE_THRESHOLD", "-1"))
if SMALLTALK_LOG_TIMEOUT == -1:
    raise RuntimeError("GAZE_THRESHOLD not set")

SIM_THRESHOLD: float = float(os.getenv("SIM_THRESHOLD", "-1"))
if SIM_THRESHOLD == -1:
    raise RuntimeError("SIM_THRESHOLD not set")

GAZE_THRESHOLD: float = float(os.getenv("GAZE_THRESHOLD", "-1"))
if GAZE_THRESHOLD == -1:
    raise RuntimeError("GAZE_THRESHOLD not set")

AUTO_LOCK_DELAY: float = float(os.getenv("AUTO_LOCK_DELAY", "-1"))
if AUTO_LOCK_DELAY == -1:
    raise RuntimeError("AUTO_LOCK_DELAY not set")

SHIELD_DELAY: float = float(os.getenv("SHIELD_DELAY", "-1"))
if SHIELD_DELAY == -1:
    raise RuntimeError("SHIELD_DELAY not set")