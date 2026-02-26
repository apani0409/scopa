"""
src/decks/napolitane.py
=======================
Self-registering module for the traditional 40-card Neapolitan deck.

How it works
------------
Importing this module (or ``src.decks``) triggers the ``register()`` call at
the bottom of this file.  After that, anywhere in the application you can do::

    from src.engine import DeckRegistry, loadDeck
    cards = loadDeck("napolitane")

Asset path resolution
---------------------
The path is resolved *at import time* relative to this source file so the
engine works regardless of the current working directory::

    src/decks/napolitane.py
          ↑
    parent  → src/decks/
    parent  → src/
    parent  → project root  (e.g. /home/sandro/Dev/Apps/scopa)
    / "napolitane"  → /home/sandro/Dev/Apps/scopa/napolitane

This keeps ``DeckDefinition.asset_path`` as an absolute path, which makes
filesystem validation in the loader unambiguous.

Adding future decks
-------------------
Copy this file, change ``_DECK_NAME``, ``_ASSET_PATH``, and optionally
declare additional ``art_variants``.  The rest of the engine needs zero
changes — it is fully deck-agnostic.

    # src/decks/bergamasche.py  (example)
    _DECK_NAME  = "bergamasche"
    _ASSET_PATH = Path(__file__).resolve().parent.parent.parent / "bergamasche"
    ...
    DeckRegistry.register(_build_definition())
"""

from __future__ import annotations

from pathlib import Path

from ..engine.metadata import load_metadata
from ..engine.models import DeckDefinition, NAPOLITANE_SUITS, STANDARD_VALUES
from ..engine.registry import DeckRegistry

# ── Constants ─────────────────────────────────────────────────────────────────

_DECK_NAME: str = "napolitane"

#: Absolute path to the deck's asset root, resolved from this file's location.
#: Structure expected:
#:   <_ASSET_PATH>/
#:       bastoni/  1_bastoni.png … 10_bastoni.png
#:       coppe/    1_coppe.png   … 10_coppe.png
#:       oro/      1_oro.png     … 10_oro.png
#:       spade/    1_spade.png   … 10_spade.png
#:       metadata.json            (optional)
_ASSET_PATH: Path = (
    Path(__file__).resolve()   # …/src/decks/napolitane.py
    .parent                    # …/src/decks/
    .parent                    # …/src/
    .parent                    # project root
    / "napolitane"
)


# ── Definition builder ────────────────────────────────────────────────────────

def _build_definition() -> DeckDefinition:
    """
    Construct the :class:`~src.engine.models.DeckDefinition` for the
    Neapolitan deck.

    Attempts to load ``metadata.json`` from the asset directory; silently
    proceeds with ``metadata=None`` when the file is absent so that the
    deck is usable even in minimal / test environments.
    """
    metadata = load_metadata(str(_ASSET_PATH))  # None if file absent

    return DeckDefinition(
        name=_DECK_NAME,
        suits=NAPOLITANE_SUITS,
        values=STANDARD_VALUES,
        asset_path=str(_ASSET_PATH),
        # Declare additional artwork variants here as you add asset folders.
        # e.g.: art_variants=("default", "vintage", "hi-res")
        art_variants=("default",),
        metadata=metadata,
    )


# ── Eager registration ────────────────────────────────────────────────────────
# Runs once when this module is first imported.  Subsequent imports are
# no-ops thanks to Python's module cache.

DeckRegistry.register(_build_definition())
