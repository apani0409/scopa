"""
src/engine/registry.py
======================
Central registry for all deck definitions.

Design
------
``DeckRegistry`` is a *class-level* (singleton-style) store — no instance is
ever needed.  Deck modules register themselves on import, so the caller only
has to ``import src.decks.napolitane`` (or ``from src.decks import *``) and the
deck becomes available everywhere.

Thread safety
-------------
The registry mutates a class-level dict.  For a single-threaded game process
this is fine.  If you ever add networking / hot-reload, wrap ``register`` /
``unregister`` with a ``threading.Lock``.

Usage
-----
::

    from src.engine.registry import DeckRegistry

    DeckRegistry.register(my_definition)
    defn = DeckRegistry.get("napolitane")
    print(DeckRegistry.list_decks())
"""

from __future__ import annotations

from .models import DeckDefinition
from .exceptions import DeckNotFoundError, InvalidDeckDefinitionError

_REQUIRED_CARD_COUNT: int = 40


class DeckRegistry:
    """
    Class-level store of :class:`~src.engine.models.DeckDefinition` objects.

    All public methods are ``@classmethod``; never instantiate this class.
    """

    _decks: dict[str, DeckDefinition] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    @classmethod
    def register(cls, deck: DeckDefinition) -> None:
        """
        Validate *deck* and add it to the registry.

        Raises
        ------
        InvalidDeckDefinitionError
            If any structural constraint is violated (see
            :py:meth:`_validate_definition`).
        """
        cls._validate_definition(deck)
        cls._decks[deck.name] = deck

    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Remove *name* from the registry.

        No-op if the name is not present (safe to call in teardown / tests).
        """
        cls._decks.pop(name, None)

    @classmethod
    def clear(cls) -> None:
        """Remove **all** registered decks.  Primarily useful in test suites."""
        cls._decks.clear()

    # ── Lookup ────────────────────────────────────────────────────────────────

    @classmethod
    def get(cls, name: str) -> DeckDefinition:
        """
        Return the :class:`~src.engine.models.DeckDefinition` registered under
        *name*.

        Raises
        ------
        DeckNotFoundError
            If *name* has not been registered.
        """
        if name not in cls._decks:
            raise DeckNotFoundError(name, cls.list_decks())
        return cls._decks[name]

    @classmethod
    def list_decks(cls) -> list[str]:
        """Return a snapshot of all registered deck names (insertion order)."""
        return list(cls._decks.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Return ``True`` if *name* is currently in the registry."""
        return name in cls._decks

    # ── Validation ────────────────────────────────────────────────────────────

    @classmethod
    def _validate_definition(cls, deck: DeckDefinition) -> None:
        """
        Accumulate all constraint violations and raise a single
        :class:`~src.engine.exceptions.InvalidDeckDefinitionError` listing all
        of them, so the developer can fix everything in one pass.

        Constraints
        -----------
        * ``name`` must be a non-empty string.
        * ``suits`` must have no duplicates.
        * ``values`` must have no duplicates.
        * ``len(suits) × len(values)`` must equal exactly 40.
        * ``asset_path`` must be a non-empty string.
        * Every declared ``art_variant`` must be a non-empty string.
        * ``"default"`` must be present in ``art_variants``.
        """
        errors: list[str] = []

        # Name
        if not deck.name or not deck.name.strip():
            errors.append("Deck name cannot be empty.")

        # Suits
        if len(set(deck.suits)) != len(deck.suits):
            dupes = [s for s in deck.suits if deck.suits.count(s) > 1]
            errors.append(f"Duplicate suits detected: {sorted(set(dupes))}.")

        # Values
        if len(set(deck.values)) != len(deck.values):
            dupes = [v for v in deck.values if deck.values.count(v) > 1]
            errors.append(f"Duplicate values detected: {sorted(set(dupes))}.")

        # Card count
        count = deck.expected_card_count
        if count != _REQUIRED_CARD_COUNT:
            errors.append(
                f"Deck must define exactly {_REQUIRED_CARD_COUNT} cards "
                f"({len(deck.suits)} suits × {len(deck.values)} values = {count})."
            )

        # Asset path
        if not deck.asset_path or not deck.asset_path.strip():
            errors.append("asset_path cannot be empty.")

        # Art variants
        if not deck.art_variants:
            errors.append("art_variants must contain at least one entry.")
        else:
            if "default" not in deck.art_variants:
                errors.append(
                    "'default' must be listed in art_variants "
                    "(it is the canonical asset layout)."
                )
            bad = [v for v in deck.art_variants if not v or not v.strip()]
            if bad:
                errors.append(
                    f"art_variants contains empty or blank entries: {bad!r}."
                )

        if errors:
            bullet_list = "\n".join(f"  • {e}" for e in errors)
            raise InvalidDeckDefinitionError(
                f"DeckDefinition '{deck.name}' failed validation:\n{bullet_list}"
            )
