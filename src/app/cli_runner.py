"""
src/app/cli_runner.py
=====================
Interactive command-line interface — Human vs AI Scopa.

Run from the project root::

    python -m src.app.cli_runner

Architecture note
-----------------
This file is the thinnest possible layer between the human and
``GameSession``.  It contains **zero** game logic:

* All rules live in ``ScopaEngine`` (``src/engine/scopa.py``).
* All turn routing lives in ``GameSession`` (``src/app/game_session.py``).
* All move selection lives in ``SimpleAI`` (``src/app/ai_player.py``).

This module only does:
1. Render ``get_public_state()`` dicts as formatted text.
2. Parse keyboard input into ``(card_id, capture_ids)`` pairs.
3. Call ``play_human_move`` / ``play_ai_turn`` / ``get_final_scores``.
4. Display AI actions and end-of-round summaries.

The CLI acts as an integration-validation harness for the application layer
before a real UI (web/mobile) is connected.
"""

from __future__ import annotations

import sys
from typing import Optional

from src.engine import (
    Card,
    CardNotInHandError,
    EqualValuePriorityError,
    InvalidCaptureError,
    ScopaEngineError,
    WrongTurnError,
)

from .game_session import GameSession

# ── Display constants ─────────────────────────────────────────────────────────

_W    = 58
_BOLD = "━" * _W
_THIN = "─" * _W

_SUIT_LABEL: dict[str, str] = {
    "bastoni": "Bastoni 🪵",
    "coppe":   "Coppe   🏆",
    "oro":     "Oro     🪙",
    "spade":   "Spade   ⚔️ ",
}

_VALUE_NAME: dict[int, str] = {
    1: "Asso", 2: "Due", 3: "Tre", 4: "Quattro", 5: "Cinque",
    6: "Sei",  7: "Sette", 8: "Otto", 9: "Nove", 10: "Re",
}


def _card_label(card_data: dict) -> str:
    """
    Format a card dict as a short human-readable string.

    Example: ``" 7 Oro     🪙"`` (right-aligned value, fixed-width suit).
    """
    value = card_data["value"]
    suit  = card_data["suit"]
    name  = _VALUE_NAME.get(value, str(value))
    suit_label = _SUIT_LABEL.get(suit, suit.capitalize())
    return f"{value:>2} {name:<9} {suit_label}"


def _card_from_dict(data: dict) -> Card:
    """Reconstruct a display-only ``Card`` from a serialised dict."""
    return Card(
        id=data["id"],
        suit=data["suit"],
        value=data["value"],
        image_url=data.get("image_url", ""),
    )


def _label_from_id(card_id: str) -> str:
    """
    Build a display label from a card ID (``"deck::suit::value"``).

    Used when the actual Card is unavailable (e.g. AI's played card which
    was hidden in its hand).
    """
    parts = card_id.split("::")
    if len(parts) == 3:
        _, suit, value_str = parts
        try:
            value = int(value_str)
            name  = _VALUE_NAME.get(value, value_str)
            suit_label = _SUIT_LABEL.get(suit, suit.capitalize())
            return f"{value:>2} {name:<9} {suit_label}"
        except ValueError:
            pass
    return card_id  # fallback


# ── Output helpers ────────────────────────────────────────────────────────────

def _print_header(session: GameSession) -> None:
    pub = session.get_public_state()
    print()
    print(_BOLD)
    print(
        f"  🃏  SCOPA  ·  Round {session.round_number}"
        f"  ·  Deck: {pub['deck_remaining']} cards left"
    )
    print(_BOLD)


def _print_scores(pub: dict, human_id: str) -> None:
    print()
    for pid, info in pub["players"].items():
        label   = "You " if pid == human_id else "AI  "
        pts     = pub["scores"].get(pid, 0)
        print(
            f"  {label}  captured: {info['captured_count']:>2}  "
            f"scopas: {info['scopas']}  "
            f"pts this round: {pts}"
        )


def _print_table(pub: dict) -> None:
    table = pub["table"]
    print(f"\n  TABLE  ({len(table)} card{'s' if len(table) != 1 else ''})")
    if not table:
        print("    (empty)")
    else:
        for i, cd in enumerate(table):
            print(f"    [{i}]  {_card_label(cd)}")


def _print_hand(pub: dict) -> None:
    hand = pub["human_hand"]
    print(f"\n  YOUR HAND  ({len(hand)} card{'s' if len(hand) != 1 else ''})")
    for i, cd in enumerate(hand):
        print(f"    [{i}]  {_card_label(cd)}")


def _pause() -> None:
    """Wait for Enter before continuing (non-blocking friendly)."""
    try:
        input("      (press Enter to continue…) ")
    except (EOFError, KeyboardInterrupt):
        pass


# ── Input helpers ─────────────────────────────────────────────────────────────

def _prompt(msg: str) -> str:
    """Print *msg* as a prompt and return stripped input.  Exit on EOF/Ctrl-C."""
    try:
        return input(f"\n  {msg}\n  > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n  Goodbye!")
        sys.exit(0)


def _choose_card(session: GameSession) -> Optional[dict]:
    """
    Interactively let the human pick a card from their hand.

    Returns the raw card dict (suitable for ``_card_label``), or ``None``
    if the hand is empty (defensive — should not happen during normal play).
    """
    pub  = session.get_public_state()
    hand = pub["human_hand"]
    if not hand:
        return None

    while True:
        raw = _prompt(f"Choose a card to play  [0–{len(hand) - 1}]:")
        try:
            idx = int(raw)
            if 0 <= idx < len(hand):
                return hand[idx]
            print(f"  ✗  Enter a number from 0 to {len(hand) - 1}.")
        except ValueError:
            print("  ✗  Please enter a number.")


def _choose_capture(
    session: GameSession,
    card_dict: dict,
) -> Optional[list[str]]:
    """
    Show capture options for *card_dict* and let the human choose.

    Returns
    -------
    list[str]
        Selected capture (list of ``card_id``s) — pass to ``play_human_move``.
    list[]
        Empty list — player chose to discard.
    None
        Player cancelled (wants to re-select a different card).
    """
    pub      = session.get_public_state()
    table_by_id = {cd["id"]: cd for cd in pub["table"]}
    combos   = session.get_legal_captures(card_dict["id"])

    label = _card_label(card_dict)

    if not combos:
        print(f"\n  No captures available for {label}.")
        answer = _prompt("Discard this card?  (y / n  or  b to go back)")
        if answer.lower() in ("y", "yes", ""):
            return []
        return None  # back to card selection

    print(f"\n  CAPTURE OPTIONS for {label}:")
    for i, combo_ids in enumerate(combos, start=1):
        combo_labels = " + ".join(
            _card_label(table_by_id[cid])
            for cid in combo_ids
            if cid in table_by_id
        )
        total = sum(table_by_id[cid]["value"] for cid in combo_ids if cid in table_by_id)
        print(f"    [{i}]  {combo_labels}  (= {total})")
    print(f"    [D]  Discard (place on table, no capture)")
    print(f"    [B]  Back (choose a different card)")

    while True:
        raw = _prompt(f"Choose  [1–{len(combos)},  D,  or  B]:").upper()
        if raw == "B":
            return None
        if raw == "D":
            return []
        try:
            idx = int(raw)
            if 1 <= idx <= len(combos):
                return combos[idx - 1]
            print(f"  ✗  Enter 1–{len(combos)}, D, or B.")
        except ValueError:
            print(f"  ✗  Enter 1–{len(combos)}, D, or B.")


# ── Turn handlers ─────────────────────────────────────────────────────────────

def _play_human_turn(session: GameSession) -> None:
    """Handle a complete human turn: display → card pick → capture pick → submit."""
    _print_header(session)
    pub = session.get_public_state()
    _print_table(pub)
    _print_scores(pub, session.human_id)
    _print_hand(pub)
    print(f"\n  {_THIN}")
    print("  YOUR TURN")

    while True:
        card_dict = _choose_card(session)
        if card_dict is None:
            break

        capture_ids = _choose_capture(session, card_dict)
        if capture_ids is None:
            continue  # player pressed B — re-pick card

        try:
            session.play_human_move(card_dict["id"], capture_ids)

            # Brief feedback
            label = _card_label(card_dict)
            if capture_ids:
                print(f"\n  ✓  You played {label} and captured {len(capture_ids)} card(s).")
            else:
                print(f"\n  ✓  You discarded {label}.")
            break

        except EqualValuePriorityError as exc:
            print(f"\n  ✗  Rule violation: {exc}")
        except (InvalidCaptureError, CardNotInHandError, WrongTurnError) as exc:
            print(f"\n  ✗  {exc}")
        except ScopaEngineError as exc:
            print(f"\n  ✗  Engine error: {exc}")


def _play_ai_turn(session: GameSession) -> None:
    """Execute the AI's turn and display what it did."""
    # Snapshot the table BEFORE the move so we can describe the capture
    pub_before  = session.get_public_state()
    table_before = {cd["id"]: cd for cd in pub_before["table"]}

    print(f"\n  {_THIN}")
    print("  AI is thinking…")

    ai_card_id, ai_capture_ids = session.play_ai_turn()

    ai_label = _label_from_id(ai_card_id)
    if ai_capture_ids:
        captured_labels = "  +  ".join(
            _card_label(table_before[cid])
            for cid in ai_capture_ids
            if cid in table_before
        )
        print(f"\n  🤖  AI played    {ai_label}")
        print(f"      captured:    {captured_labels}")
    else:
        print(f"\n  🤖  AI discarded {ai_label}")

    _pause()


# ── Round / match flow ────────────────────────────────────────────────────────

def _show_round_result(result: dict, human_id: str) -> None:
    """Display the end-of-round scoring breakdown."""
    print()
    print(_BOLD)
    print(f"  ROUND {result['round_number']} COMPLETE")
    print(_BOLD)

    print("\n  Points awarded this round:")
    for pid, pts in result["round_scores"].items():
        label      = "You" if pid == human_id else "AI "
        scopas     = result["scopas"].get(pid, 0)
        scopa_note = (
            f"  (incl. {scopas} scopa{'s' if scopas != 1 else ''})"
            if scopas else ""
        )
        print(f"    {label}  {pts:>2} pt{'s' if pts != 1 else ''}{scopa_note}")

    print("\n  Session totals:")
    for pid, total in result["cumulative"].items():
        label = "You" if pid == human_id else "AI "
        print(f"    {label}  {total:>3} pts")

    print()


def play_round(session: GameSession) -> dict:
    """
    Execute one complete round from deal to score.

    Returns the result dict from ``get_final_scores()``.
    """
    session.start_round()

    while not session.is_round_over():
        if session.is_human_turn:
            _play_human_turn(session)
        else:
            _play_ai_turn(session)

    result = session.get_final_scores()
    _show_round_result(result, session.human_id)
    return result


def _ask_play_again() -> bool:
    raw = _prompt("Play another round?  (y / n)").lower()
    return raw in ("y", "yes", "")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """Interactive CLI entry point."""
    print()
    print(_BOLD)
    print("  🃏  SCOPA  ·  Human vs AI")
    print(_BOLD)

    seed_input = _prompt(
        "Enter a seed for a reproducible game, or press Enter for random:"
    )
    seed: Optional[int]
    if seed_input.isdigit():
        seed = int(seed_input)
        print(f"  Using seed: {seed}")
    else:
        import random
        seed = random.randint(0, 999_999)
        print(f"  Random seed: {seed}  (note it down to replay this game)")

    session = GameSession(seed=seed)

    while True:
        play_round(session)
        if not _ask_play_again():
            break

    print()
    print(_BOLD)
    print("  Final session totals:")
    for pid, total in session.cumulative_scores.items():
        label = "You" if pid == session.human_id else "AI "
        print(f"    {label}  {total:>3} pts")

    winner_id = max(session.cumulative_scores, key=session.cumulative_scores.get)
    if winner_id == session.human_id:
        print("\n  🎉  You win the match!  Well played.")
    else:
        print("\n  🤖  AI wins the match.  Better luck next time!")

    print(_BOLD)
    print()


if __name__ == "__main__":
    main()
