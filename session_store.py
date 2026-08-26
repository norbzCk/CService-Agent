"""
In-memory chat session store, keyed by session_id.

Note: this is single-process, in-memory storage. It's fine for a single
Render instance (no horizontal scaling), and sessions are lost on restart
or redeploy -- acceptable for a chat widget where losing history on a
rare restart is a minor inconvenience, not data loss. If you ever scale
to multiple instances, this needs to move to Redis or the database.
"""
import time
from threading import Lock

SESSION_TTL_SECONDS = 60 * 60  # 1 hour of inactivity before a session expires

_sessions: dict[str, dict] = {}
_last_used: dict[str, float] = {}
_lock = Lock()


def get_session(session_id: str) -> dict | None:
    with _lock:
        _evict_expired()
        state = _sessions.get(session_id)
        if state:
            _last_used[session_id] = time.time()
        return state


def set_session(session_id: str, state: dict) -> None:
    with _lock:
        _sessions[session_id] = state
        _last_used[session_id] = time.time()


def _evict_expired() -> None:
    now = time.time()
    expired = [sid for sid, ts in _last_used.items() if now - ts > SESSION_TTL_SECONDS]
    for sid in expired:
        _sessions.pop(sid, None)
        _last_used.pop(sid, None)


def active_session_count() -> int:
    with _lock:
        _evict_expired()
        return len(_sessions)
