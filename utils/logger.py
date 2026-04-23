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
    _append(username, record)


def log_feedback(
    username: str,
    session_id: str,
    pdf: str,
    sentiment: str,
    question: str,
    answer: str,
) -> None:
    """Append a user feedback event (thumbs up/down) to the JSONL chat log.

    Args:
        sentiment: 'positive' or 'negative'
        question:  the user question the feedback refers to
        answer:    the assistant answer that was rated
    """
    record = {
        "session_id": session_id,
        "user_id":    username,
        "pdf":        pdf,
        "timestamp":  datetime.now().isoformat(timespec="seconds"),
        "role":       "feedback",
        "sentiment":  sentiment,
        "question":   question,
        "answer":     answer,
    }
    _append(username, record)


def _append(username: str, record: dict) -> None:
    log_path = os.path.join(LOGS_DIR, f"{username}_chat_history.jsonl")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
