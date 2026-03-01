import urllib.request
import json

from .env_vars import SMALLTALK_LOG_TIMEOUT, SMALLTALK_LOG_URL
def st_post(payload: dict):
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            SMALLTALK_LOG_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=SMALLTALK_LOG_TIMEOUT):
            pass
    except Exception:
        # Logging must NEVER block detection loop
        pass