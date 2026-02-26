"""
src/decks/__init__.py
=====================
Deck registration package.

Importing ``src.decks`` (or any symbol from it) auto-registers all bundled
decks with :class:`~src.engine.registry.DeckRegistry`.

To add a new deck:
    1. Create ``src/decks/my_new_deck.py`` following the pattern in
       ``napolitane.py``.
    2. Add ``from . import my_new_deck`` below.
    3. Drop the card assets in the appropriate folder.

No changes to the engine or game logic are needed.
"""

from . import napolitane  # registers "napolitane"

# Future decks — uncomment as you add them:
# from . import bergamasche   # registers "bergamasche"
# from . import bolognese     # registers "bolognese"

__all__ = ["napolitane"]
