"""
src/engine/__init__.py
======================
Public API surface of the Scopa game engine.

Import from here, not from sub-modules, to get a stable interface::

    from src.engine import Card, DeckDefinition, DeckRegistry, loadDeck

Re-exports everything downstream code needs; internal helpers stay private.
"""

from .exceptions import (
    DeckNotFoundError,
    IncompleteDeckError,
    InvalidDeckDefinitionError,
    MissingCardImageError,
    ScopaEngineError,
)
from .loader import loadDeck
from .metadata import load_metadata
from .models import (
    NAPOLITANE_SUITS,
    STANDARD_VALUES,
    Card,
    DeckDefinition,
    DeckMetadata,
)
from .registry import DeckRegistry
from .scopa import (
    CardNotInHandError,
    EqualValuePriorityError,
    GameConfig,
    GameState,
    InvalidCaptureError,
    PlayerState,
    ScopaEngine,
    WrongTurnError,
)

__all__ = [
    # Models
    "Card",
    "DeckDefinition",
    "DeckMetadata",
    "NAPOLITANE_SUITS",
    "STANDARD_VALUES",
    # Registry
    "DeckRegistry",
    # Loader
    "loadDeck",
    # Metadata utility
    "load_metadata",
    # Game engine
    "GameConfig",
    "GameState",
    "PlayerState",
    "ScopaEngine",
    # Game-play exceptions
    "ScopaEngineError",
    "DeckNotFoundError",
    "InvalidDeckDefinitionError",
    "IncompleteDeckError",
    "MissingCardImageError",
    "WrongTurnError",
    "CardNotInHandError",
    "InvalidCaptureError",
    "EqualValuePriorityError",
]
