"""
src/multiplayer
==============
FastAPI multiplayer layer for the Scopa game.

Public API
----------
* ``MultiplayerGameSession`` — ScopaEngine wrapper for 2-human play
* ``MultiplayerSession``     — WebSocket session (connections + game + status)
* ``manager``                — global in-memory SessionManager singleton
* ``app``                    — FastAPI application (see server.py)
"""

from .models import MultiplayerGameSession, MultiplayerSession
from .manager import manager

__all__ = [
    "MultiplayerGameSession",
    "MultiplayerSession",
    "manager",
]
