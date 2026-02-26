"""
src/engine/exceptions.py
========================
All domain exceptions raised by the Scopa engine.

Hierarchy
---------
ScopaEngineError                  ← base; catch-all for engine errors
├── DeckNotFoundError             ← registry lookup failure
├── InvalidDeckDefinitionError    ← structural problem in a DeckDefinition
├── IncompleteDeckError           ← loaded deck has wrong card count
└── MissingCardImageError         ← expected image file not found on disk
"""


class ScopaEngineError(Exception):
    """Base class for all Scopa engine exceptions."""


# ── Registry ──────────────────────────────────────────────────────────────────

class DeckNotFoundError(ScopaEngineError):
    """
    Raised when :py:meth:`~src.engine.registry.DeckRegistry.get` is called
    with a name that has not been registered.

    Attributes
    ----------
    name:       The requested (unknown) deck name.
    available:  Names currently in the registry at the time of the call.
    """

    def __init__(self, name: str, available: list[str]) -> None:
        display = available if available else ["(none registered)"]
        super().__init__(
            f"Deck '{name}' is not registered.  "
            f"Available decks: {display}"
        )
        self.name = name
        self.available = available


class InvalidDeckDefinitionError(ScopaEngineError):
    """
    Raised by :py:meth:`~src.engine.registry.DeckRegistry.register` when a
    :class:`~src.engine.models.DeckDefinition` fails structural validation.

    The exception message lists every individual violation found.
    """


# ── Loader ────────────────────────────────────────────────────────────────────

class IncompleteDeckError(ScopaEngineError):
    """
    Raised when the cards produced by :func:`~src.engine.loader.loadDeck`
    do not equal the expected count (40).

    Attributes
    ----------
    name:      The deck name that was being loaded.
    expected:  How many cards the definition declares.
    got:       How many cards were actually produced.
    """

    def __init__(self, name: str, expected: int, got: int) -> None:
        super().__init__(
            f"Deck '{name}' is incomplete: "
            f"expected {expected} cards, got {got}."
        )
        self.name = name
        self.expected = expected
        self.got = got


class MissingCardImageError(ScopaEngineError):
    """
    Raised when a required card image cannot be found on the local filesystem.

    Attributes
    ----------
    suit:   Suit name of the missing card.
    value:  Value of the missing card.
    url:    Resolved path / URL that was checked.
    """

    def __init__(self, suit: str, value: int, url: str) -> None:
        super().__init__(
            f"Missing image for '{value} of {suit}': '{url}'"
        )
        self.suit = suit
        self.value = value
        self.url = url
