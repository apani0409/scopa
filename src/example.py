"""
src/example.py
==============
Demonstrates the complete deck loading system end-to-end.

Run from the project root::

    python -m src.example

Nothing in this file is required by the game engine — it is purely
illustrative.
"""

from __future__ import annotations

# ── Step 0: trigger deck registration ────────────────────────────────────────
# Importing src.decks auto-registers all bundled deck definitions.
# The game engine itself never calls this — the application bootstrap does.
import src.decks  # noqa: F401

from src.engine import (
    Card,
    DeckDefinition,
    DeckRegistry,
    loadDeck,
)
from src.engine.exceptions import (
    DeckNotFoundError,
    MissingCardImageError,
)

_SEP = "─" * 60


def _section(title: str) -> None:
    print(f"\n{_SEP}\n  {title}\n{_SEP}")


# ── 1. Inspect the registry ───────────────────────────────────────────────────

def demo_registry() -> DeckDefinition:
    _section("1 · Registry")

    print(f"Registered decks : {DeckRegistry.list_decks()}")

    defn = DeckRegistry.get("napolitane")
    print(f"Name             : {defn.name}")
    print(f"Suits            : {defn.suits}")
    print(f"Values           : {defn.values}")
    print(f"Asset path       : {defn.asset_path}")
    print(f"Art variants     : {defn.art_variants}")
    print(f"Expected cards   : {defn.expected_card_count}")

    if defn.metadata:
        m = defn.metadata
        print(f"\nMetadata")
        print(f"  Display name   : {m.display_name}")
        print(f"  Origin         : {m.origin}")
        print(f"  Aspect ratio   : {m.aspect_ratio}  (height / width)")
        print(f"  Art variant    : {m.artwork_variant}")
        print(f"  Description    : {m.description}")
    else:
        print("\n  (no metadata.json found — that's fine)")

    return defn


# ── 2. Load the deck ──────────────────────────────────────────────────────────

def demo_load() -> list[Card]:
    _section("2 · Load deck")

    try:
        cards = loadDeck("napolitane")
    except MissingCardImageError as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(1) from exc

    print(f"Loaded {len(cards)} cards.\n")

    # Show first five cards
    for card in cards[:5]:
        print(
            f"  {str(card):<22}  "
            f"id={card.id!r:<40}  "
            f"url={card.image_url}"
        )
    print("  … (35 more)")

    return cards


# ── 3. Game-engine usage (no image paths involved) ────────────────────────────

def demo_game_logic(cards: list[Card]) -> None:
    _section("3 · Game-engine logic (suit / value only)")

    # Filter by suit
    bastoni = [c for c in cards if c.suit == "bastoni"]
    print(f"Bastoni cards          : {len(bastoni)}")
    print(f"Bastoni values         : {[c.value for c in bastoni]}")

    # Find a specific card
    sette_oro = next(c for c in cards if c.suit == "oro" and c.value == 7)
    print(f"7 of Oro               : {sette_oro}")
    print(f"  id                   : {sette_oro.id!r}")

    # Score example: sette bello (7 of gold) is worth 21 in Scopa scoring
    scopa_values = {7: 21, 6: 18, 1: 16, 5: 15, 4: 14, 3: 13, 2: 12}
    score = scopa_values.get(sette_oro.value, sette_oro.value)
    print(f"  Scopa (primiera) pts : {score}")

    # Verify the engine never inspects image_url for logic
    suits_found = {c.suit for c in cards}
    assert suits_found == {"bastoni", "coppe", "oro", "spade"}, "Suit mismatch!"
    assert all(1 <= c.value <= 10 for c in cards), "Value out of range!"
    assert len({c.id for c in cards}) == 40, "Duplicate card IDs!"
    print("\n  ✓ All integrity assertions passed.")


# ── 4. Error handling ─────────────────────────────────────────────────────────

def demo_errors() -> None:
    _section("4 · Error handling")

    # Unknown deck
    try:
        loadDeck("bergamasche")
    except DeckNotFoundError as exc:
        print(f"[Expected DeckNotFoundError]\n  {exc}")

    # Unknown art variant
    try:
        loadDeck("napolitane", art_variant="nonexistent")
    except ValueError as exc:
        print(f"\n[Expected ValueError]\n  {exc}")


# ── 5. Scalability preview ────────────────────────────────────────────────────

def demo_scalability() -> None:
    _section("5 · Scalability hooks")

    print("To add a new deck (e.g. Bergamasche):")
    print("  1. Place assets in  napolitane/../bergamasche/{suit}/{value}_{suit}.png")
    print("  2. Create           src/decks/bergamasche.py  (copy napolitane.py)")
    print("  3. Uncomment        '# from . import bergamasche'  in src/decks/__init__.py")
    print("  4. Call             loadDeck('bergamasche')  — done.")
    print()
    print("To add an alternate artwork set:")
    print("  1. Place assets in  napolitane/vintage/{suit}/{value}_{suit}.png")
    print("  2. Add 'vintage' to art_variants in src/decks/napolitane.py")
    print("  3. Call             loadDeck('napolitane', art_variant='vintage')")
    print()
    print("To support metadata:")
    print("  1. Drop a metadata.json in the deck asset root")
    print("  2. It is loaded automatically — no code changes needed.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    print("═" * 60)
    print("  Scopa Deck Loader — end-to-end demonstration")
    print("═" * 60)

    demo_registry()
    cards = demo_load()
    demo_game_logic(cards)
    demo_errors()
    demo_scalability()

    print(f"\n{'═' * 60}")
    print("  All demos completed successfully.")
    print("═" * 60)


if __name__ == "__main__":
    main()
