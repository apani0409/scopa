"""
src/multiplayer/manager.py
==========================
Global in-memory session store.

``SessionManager`` is intentionally simple: a dict keyed by ``session_id``
and a secondary dict keyed by ``join_code``.  For a production deployment
with multiple server replicas, replace the two dicts with Redis hashes
and use ``redis.asyncio`` — see the deployment notes in the project README.

Usage
-----
::

    session, player_id = manager.create_session()
    session, joiner_id = manager.join_session(join_code)
    session            = manager.get_session(session_id)
"""

from __future__ import annotations

import secrets
import string
import time
import uuid

from .models import MultiplayerSession

_CLEANUP_AFTER_SECONDS = 3_600        # abandon sessions idle > 1 h
_JOIN_CODE_ALPHABET    = string.ascii_uppercase + string.digits
_JOIN_CODE_LENGTH      = 6


# ── ID generators ─────────────────────────────────────────────────────────────

def _gen_join_code() -> str:
    return "".join(
        secrets.choice(_JOIN_CODE_ALPHABET) for _ in range(_JOIN_CODE_LENGTH)
    )


def _gen_player_id() -> str:
    return str(uuid.uuid4())[:8]


def _gen_session_id() -> str:
    return str(uuid.uuid4())


# ── Manager ───────────────────────────────────────────────────────────────────

class SessionManager:
    """
    Async-safe global session store.

    All methods are synchronous (no ``await``) — they mutate plain dicts
    and strings.  The only async concern is within each session, handled
    by ``MultiplayerSession._lock``.
    """

    def __init__(self) -> None:
        self._sessions:   dict[str, MultiplayerSession] = {}
        self._join_codes: dict[str, str]                = {}  # join_code → session_id

    # ── Session lifecycle ─────────────────────────────────────────────────────

    def create_session(self) -> tuple[MultiplayerSession, str]:
        """
        Create a new session waiting for a second player.

        Returns
        -------
        (session, creator_player_id)
        """
        session_id = _gen_session_id()
        join_code  = self._unique_join_code()
        creator_id = _gen_player_id()

        session = MultiplayerSession(
            session_id=session_id,
            join_code=join_code,
            player_ids=[creator_id],
        )
        self._sessions[session_id]  = session
        self._join_codes[join_code] = session_id
        return session, creator_id

    def join_session(self, join_code: str) -> tuple[MultiplayerSession, str]:
        """
        Join an existing session by its join code.

        Parameters
        ----------
        join_code:
            Case-insensitive 6-character code produced by ``create_session``.

        Returns
        -------
        (session, joiner_player_id)

        Raises
        ------
        KeyError
            If *join_code* is not found.
        ValueError
            If the session is full or no longer in ``"waiting"`` state.
        """
        join_code  = join_code.strip().upper()
        session_id = self._join_codes.get(join_code)
        if session_id is None:
            raise KeyError(f"Join code '{join_code}' not found.")

        session = self._sessions[session_id]
        if session.status != "waiting":
            raise ValueError("Session is no longer accepting players.")
        if len(session.player_ids) >= 2:
            raise ValueError("Session is already full.")

        joiner_id = _gen_player_id()
        session.player_ids.append(joiner_id)
        return session, joiner_id

    def get_session(self, session_id: str) -> MultiplayerSession:
        """
        Retrieve a session by ID.

        Raises
        ------
        KeyError
            If *session_id* is not found.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Session '{session_id}' not found.")
        return session

    def abandon_session(self, session_id: str) -> None:
        """Mark a session as abandoned without removing it."""
        session = self._sessions.get(session_id)
        if session:
            session.status = "abandoned"

    # ── Maintenance ───────────────────────────────────────────────────────────

    def cleanup_old_sessions(self) -> int:
        """
        Remove sessions older than ``_CLEANUP_AFTER_SECONDS``.

        Returns
        -------
        int
            Number of sessions removed.
        """
        now = time.time()
        stale = [
            sid
            for sid, s in self._sessions.items()
            if now - s.created_at > _CLEANUP_AFTER_SECONDS
        ]
        for sid in stale:
            session = self._sessions.pop(sid, None)
            if session:
                self._join_codes.pop(session.join_code, None)
        return len(stale)

    def _unique_join_code(self) -> str:
        """Generate a join code that is not already in use."""
        while True:
            code = _gen_join_code()
            if code not in self._join_codes:
                return code


# ── Global singleton ──────────────────────────────────────────────────────────
# Imported directly by routers; replace with a Redis-backed class for
# multi-replica deployments.
manager = SessionManager()
