"""
src/app/__init__.py
===================
Public API of the Scopa application layer.

Import from here::

    from src.app import GameSession, SimpleAI, serialize_public_state
"""

from .ai_player import AIStrategy, SimpleAI
from .game_session import GameSession
from .serializer import (
    deserialize_game_state,
    export_game_state,
    load_game_state,
    serialize_game_state,
    serialize_public_state,
)

__all__ = [
    # Session orchestrator
    "GameSession",
    # AI strategies
    "AIStrategy",
    "SimpleAI",
    # Serialization
    "serialize_public_state",
    "serialize_game_state",
    "deserialize_game_state",
    "export_game_state",
    "load_game_state",
]
