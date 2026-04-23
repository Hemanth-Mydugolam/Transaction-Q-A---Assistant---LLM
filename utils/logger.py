import os
import json
from datetime import datetime

LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)


def log_message(username: str, session_id: str, pdf: str, role: str, content: str) -> None:
    """Append one message event to the user's JSONL chat log."""
    record = {
        "session_id": session_id,
        "user_id":    username,
        "pdf":        pdf,
        "timestamp":  datetime.now().isoformat(timespec="seconds"),
        "role":       role,
        "content":    content,
    }
    log_path = os.path.join(LOGS_DIR, f"{username}_chat_history.jsonl")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
