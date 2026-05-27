import threading

_lock = threading.Lock()
_sessions: dict[
    str, dict
] = {}  # {session_key: {an_session, as_session, an_creds, as_creds, as_app_no, as_email_id}}


def store(key: str, data: dict) -> None:
    with _lock:
        _sessions[key] = data


def get(key: str) -> dict | None:
    with _lock:
        return _sessions.get(key)


def remove(key: str) -> None:
    with _lock:
        _sessions.pop(key, None)
