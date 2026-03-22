"""Shared utility helpers for DataPeek."""

import uuid


def generate_session_id() -> str:
    """Return a random UUID string for session identification."""
    return uuid.uuid4().hex


def get_session(sessions: dict, session_id: str) -> dict | None:
    """Return the session dict for *session_id*, or None if absent."""
    return sessions.get(session_id)


def clear_session(sessions: dict, session_id: str) -> None:
    """Purge all data for *session_id* from memory."""
    sessions.pop(session_id, None)


def human_readable_size(size_bytes: int) -> str:
    """Convert a byte count to a human-readable string, e.g. '128.4 MB'."""
    if size_bytes < 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} B"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"
