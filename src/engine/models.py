"""
src/engine/models.py
====================
Pure data models for the Scopa game engine.

Rules
-----
- ``Card``           → the only object the game engine ever touches.
- ``DeckDefinition`` → tells the loader *what* a deck is and *where* assets live.
- ``DeckMetadata``   → rich, optional descriptor hydrated from ``metadata.json``.

The game engine must remain completely image-path-agnostic.
``Card.image_url`` is an opaque rendering attachment; game logic must never
branch on it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ── Canonical constants ───────────────────────────────────────────────────────

#: Suits of the Neapolitan (and many other Italian regional) decks.
NAPOLITANE_SUITS: tuple[str, ...] = ("bastoni", "coppe", "oro", "spade")

#: Standard Italian deck values — 1 (asso) through 10 (re).
STANDARD_VALUES: tuple[int, ...] = tuple(range(1, 11))


# ── Core game model ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Card:
    """
    Immutable representation of a single playing card.

    The game engine operates exclusively on these objects.
    ``image_url`` is populated at load-time and is intentionally opaque to
    game logic — treat it as a rendering attachment, *not* a game dependency.

    Attributes
    ----------
    suit:
        One of the deck's declared suit names (e.g. ``"bastoni"``).
    value:
        Numeric card rank, 1–10.
    id:
        Globally unique identifier within a loaded deck,
        formatted as ``"{deck_name}::{suit}::{value}"``.
    image_url:
        Filesystem path or HTTP URL to the card face image.
        Empty string when a card is created outside a load context.
    """

    suit: str
    value: int
    id: str
    image_url: str = ""

    def __post_init__(self) -> None:
        if not self.suit:
            raise ValueError("Card.suit cannot be empty.")
        if not (1 <= self.value <= 10):
            raise ValueError(
                f"Card.value must be in range 1–10, got {self.value!r}."
            )
        if not self.id:
            raise ValueError("Card.id cannot be empty.")

    # ── Convenience ───────────────────────────────────────────────────────────

    def __str__(self) -> str:
        return f"{self.value} of {self.suit}"

    def __repr__(self) -> str:
        return f"Card(suit={self.suit!r}, value={self.value}, id={self.id!r})"


# ── Deck metadata (hydrated from metadata.json) ───────────────────────────────

@dataclass
class DeckMetadata:
    """
    Rich, human-readable descriptor for a deck.

    Intended to be hydrated from a ``metadata.json`` file placed in the
    deck's asset root directory (see :mod:`src.engine.metadata`).

    Supports future extensions without breaking existing deck registrations:
    any unknown JSON keys are silently ignored by the loader.

    Example ``metadata.json``::

        {
            "display_name":   "Napoletane",
            "origin":         "Naples, Italy",
            "aspect_ratio":   1.8,
            "artwork_variant": "default",
            "description":    "Traditional 40-card Neapolitan deck."
        }

    Attributes
    ----------
    display_name:
        Human-readable deck title shown in UI / logs.
    origin:
        Geographic or cultural origin of the deck design.
    aspect_ratio:
        Card height ÷ card width (e.g. 1.8).  Used by renderers to
        allocate the correct canvas space without hardcoding pixel sizes.
    artwork_variant:
        Active artwork set identifier (e.g. ``"default"``, ``"vintage"``).
    description:
        Free-form description / credits.
    """

    display_name: str
    origin: str
    aspect_ratio: float       # height / width  — drives renderer layout
    artwork_variant: str = "default"
    description: str = ""


# ── Deck definition ───────────────────────────────────────────────────────────

@dataclass
class DeckDefinition:
    """
    Blueprint that describes a complete deck to the loader.

    ``asset_path`` is intentionally a plain string so it can hold:

    * An absolute filesystem path — ``/srv/app/assets/decks/napolitane``
    * A relative filesystem path — ``assets/decks/napolitane``
    * A CDN / HTTP URL base      — ``https://cdn.example.com/decks/napolitane``

    The loader resolves it contextually (see :mod:`src.engine.loader`).

    Attributes
    ----------
    name:
        Registry key, e.g. ``"napolitane"``.  Must be unique across the registry.
    suits:
        Ordered tuple of suit names.  Their order defines card ordering in a
        loaded deck.
    values:
        Ordered tuple of integer ranks (typically ``(1, 2, …, 10)``).
    asset_path:
        Root directory (or URL base) that contains per-suit sub-directories.
    art_variants:
        Declared artwork sets.  ``"default"`` always refers to the canonical
        ``{asset_path}/{suit}/{value}_{suit}.png`` layout.  Additional
        variants resolve to ``{asset_path}/{variant}/{suit}/{value}_{suit}.png``.
    metadata:
        Optional rich descriptor.  Loaded automatically from ``metadata.json``
        when present; ``None`` otherwise.
    """

    name: str
    suits: tuple[str, ...]
    values: tuple[int, ...]
    asset_path: str
    art_variants: tuple[str, ...] = ("default",)
    metadata: Optional[DeckMetadata] = None

    # ── Derived helpers ───────────────────────────────────────────────────────

    @property
    def expected_card_count(self) -> int:
        """Total cards this definition should produce: ``len(suits) × len(values)``."""
        return len(self.suits) * len(self.values)
