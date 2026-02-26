"""
src/simulation.py
=================
Full simulation test harness for the Scopa game engine.

Run from the project root::

    python -m src.simulation

Simulates ``SIMULATION_ROUNDS`` complete rounds of 2-player Scopa using only
legal moves produced by the engine's own capture-enumeration helper.  Every
round is deterministic: the deck shuffle and move-selection RNG both derive
their seed from ``SEED_BASE + round_number``.

Design rules
------------
* Treats ``ScopaEngine`` as a black box — all interaction is through the
  public API (``create_game``, ``play_card``, ``deal_if_needed``,
  ``is_round_over``, ``calculate_round_score``), with the sole exception of
  the explicitly documented helper ``_find_sum_combinations`` which is
  provided for exactly this kind of external move-generation use.
* Never mutates engine state directly.
* Fails fast: the first unexpected exception aborts the run after printing a
  compact state snapshot and re-raising.
"""

from __future__ import annotations

import random
import sys
import traceback
from dataclasses import dataclass, field
from typing import Optional

# ── Simulation parameters ──────────────────────────────────────────────────────

#: Total rounds to simulate.
SIMULATION_ROUNDS: int = 1000

#: RNG seed base.  Round *n* uses ``SEED_BASE + n`` for both shuffle and moves.
SEED_BASE: int = 42

#: Fixed player identifiers used across every round.
PLAYER_IDS: list[str] = ["P1", "P2"]

# ── Local game-rule constants (engine treated as black box) ───────────────────
# These mirror ``GameConfig`` defaults but are kept here so the harness does
# NOT depend on engine internals for its own scoring analysis.

_COINS_SUIT: str = "oro"
_SETTEBELLO_VALUE: int = 7
_SUITS: tuple[str, ...] = ("bastoni", "coppe", "oro", "spade")
_PRIMIERA_TABLE: dict[int, int] = {
    7: 21, 6: 18, 1: 16, 5: 15, 4: 14, 3: 13, 2: 12,
}
_PRIMIERA_DEFAULT: int = 10

# ── Engine imports ────────────────────────────────────────────────────────────

import src.decks  # noqa: E402 — registers "napolitane" with DeckRegistry

from src.engine import (  # noqa: E402
    Card,
    GameConfig,
    GameState,
    PlayerState,
    ScopaEngine,
    ScopaEngineError,
    loadDeck,
)


# ════════════════════════════════════════════════════════════════════════════
#  Result and statistics dataclasses
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class RoundResult:
    """
    Compact summary of one completed simulation round.

    All scoring analysis is performed *locally* in the harness from the
    final ``GameState`` — the engine's internal ``_award_most`` breakdown is
    not exposed, so each category is recomputed here independently.

    Attributes
    ----------
    round_number:
        1-based round index.
    scores:
        Engine-computed final scores keyed by player id.
    scopas:
        Scopas scored this round, keyed by player id.
    cards_captured:
        Total cards captured this round, keyed by player id.
    coins_captured:
        Oro (coins) cards captured this round, keyed by player id.
    settebello_winner:
        Player who captured the 7 of oro, or ``None`` (impossible in
        practice — exactly one player must have it, but typed Optional for
        safety).
    primiera_winner:
        Player with the higher primiera total, or ``None`` on a tie.
    cards_winner:
        Player who captured the most cards, or ``None`` on a tie.
    coins_winner:
        Player who captured the most coins, or ``None`` on a tie.
    score_winner:
        Player with the highest round score, or ``None`` on a tie.
    total_moves:
        Number of ``play_card`` calls made this round.
    """

    round_number: int
    scores: dict[str, int]
    scopas: dict[str, int]
    cards_captured: dict[str, int]
    coins_captured: dict[str, int]
    settebello_winner: Optional[str]
    primiera_winner: Optional[str]
    cards_winner: Optional[str]
    coins_winner: Optional[str]
    score_winner: Optional[str]
    total_moves: int


@dataclass
class SimStats:
    """
    Aggregate statistics accumulated across all simulation rounds.

    All counter dicts are keyed by player id.
    """

    total_rounds: int = 0
    total_moves: int = 0

    # Cumulative scores and scopas
    cumulative_scores: dict[str, int] = field(default_factory=dict)
    cumulative_scopas: dict[str, int] = field(default_factory=dict)
    scopa_events_total: int = 0
    rounds_with_scopa: int = 0

    # Category win/tie counters
    score_wins: dict[str, int] = field(default_factory=dict)
    score_ties: int = 0

    primiera_wins: dict[str, int] = field(default_factory=dict)
    primiera_ties: int = 0

    cards_wins: dict[str, int] = field(default_factory=dict)
    cards_ties: int = 0

    coins_wins: dict[str, int] = field(default_factory=dict)
    coins_ties: int = 0

    settebello_wins: dict[str, int] = field(default_factory=dict)

    # Error tracking
    unexpected_errors: int = 0


# ════════════════════════════════════════════════════════════════════════════
#  Pure helper functions (no engine calls)
# ════════════════════════════════════════════════════════════════════════════

def _compute_primiera(captured: list[Card]) -> int:
    """
    Compute the total primiera score for a set of captured cards.

    Each suit contributes the highest primiera-value card held by the player.
    A suit with no cards contributes 0 (making it impossible to win primiera
    against a player who holds cards in every suit).
    """
    total = 0
    for suit in _SUITS:
        suit_cards = [c for c in captured if c.suit == suit]
        if suit_cards:
            best = max(_PRIMIERA_TABLE.get(c.value, _PRIMIERA_DEFAULT) for c in suit_cards)
            total += best
    return total


def _strict_winner(counts: dict[str, int]) -> Optional[str]:
    """
    Return the single player with the highest count, or ``None`` on a tie.
    """
    if not counts:
        return None
    max_val = max(counts.values())
    winners = [pid for pid, v in counts.items() if v == max_val]
    return winners[0] if len(winners) == 1 else None


def _format_state_snapshot(state: GameState, round_number: int) -> str:
    """
    Produce a compact, human-readable snapshot of *state* for error output.

    Intentionally does NOT call any engine methods — reads public fields only.
    """
    table_str = [f"{c.value}{c.suit[0].upper()}" for c in state.table]
    lines = [
        f"  round     : {round_number}",
        f"  phase     : {state.phase}",
        f"  deck left : {len(state.deck)}",
        f"  table ({len(state.table):>2}) : {table_str}",
        f"  turn      : {state.current_player.id}  "
        f"(index={state.current_player_index})",
        f"  last cap  : {state.last_capture_player_id}",
    ]
    for p in state.players:
        hand_str = [f"{c.value}{c.suit[0].upper()}" for c in p.hand]
        lines.append(
            f"  {p.id:<4}  hand={hand_str}  "
            f"captured={len(p.captured):>2}  scopas={p.scopas}"
        )
    return "\n".join(lines)


def _assert_round_integrity(final: GameState) -> None:
    """
    Run all post-round invariant checks.  Raises ``AssertionError`` with a
    descriptive message on any failure.
    """
    assert final.phase == "finished", (
        f"Phase should be 'finished', got '{final.phase}'."
    )
    assert len(final.deck) == 0, (
        f"Deck not empty after round: {len(final.deck)} cards remain."
    )
    assert len(final.table) == 0, (
        f"Table not empty after scoring: "
        f"{[str(c) for c in final.table]}."
    )

    total_captured = sum(len(p.captured) for p in final.players)
    assert total_captured == 40, (
        f"Card conservation failed: {total_captured} captured (expected 40)."
    )

    all_ids: list[str] = [
        c.id
        for p in final.players
        for c in p.captured
    ]
    assert len(all_ids) == len(set(all_ids)), (
        "Duplicate card IDs detected in captured piles — "
        "a card was awarded more than once."
    )
    assert len(set(all_ids)) == 40, (
        f"Unique card ID count is {len(set(all_ids))}, expected 40."
    )


# ════════════════════════════════════════════════════════════════════════════
#  Move selection
# ════════════════════════════════════════════════════════════════════════════

def _select_move(
    engine: ScopaEngine,
    state: GameState,
    rng: random.Random,
) -> tuple[str, list[str]]:
    """
    Choose a legal move for the current player.

    Strategy
    --------
    1. For every card in the current player's hand, enumerate all legal
       capture sets via ``engine._find_sum_combinations``.  This method
       already encodes the equal-value priority rule — if an exact match
       exists it is the *only* option returned, so any combo from it is
       guaranteed legal.
    2. If any capturing move exists, pick one uniformly at random.
    3. Otherwise, pick a hand card uniformly at random and discard it
       (pass ``capture_ids=[]``).

    Returns
    -------
    (card_id, capture_ids)
        Ready to pass directly to ``engine.play_card``.
    """
    player = state.current_player
    capturing_moves: list[tuple[Card, list[Card]]] = []

    for card in player.hand:
        combos = engine._find_sum_combinations(card.value, state.table)
        for combo in combos:
            capturing_moves.append((card, combo))

    if capturing_moves:
        card, combo = rng.choice(capturing_moves)
        return card.id, [c.id for c in combo]

    # No capture available — discard a random card
    discard = rng.choice(player.hand)
    return discard.id, []


# ════════════════════════════════════════════════════════════════════════════
#  Core simulation functions
# ════════════════════════════════════════════════════════════════════════════

def simulate_one_round(round_number: int) -> RoundResult:
    """
    Simulate a complete Scopa round and return a :class:`RoundResult`.

    Both the deck shuffle and move-selection RNG are seeded with
    ``SEED_BASE + round_number`` so every round is independently
    reproducible.

    Parameters
    ----------
    round_number:
        1-based round index.  Used for seed derivation and error messages.

    Returns
    -------
    RoundResult
        Validated summary of the completed round.

    Raises
    ------
    AssertionError
        If any post-round invariant is violated.
    Exception
        Any unexpected engine exception is re-raised after printing a compact
        state snapshot.
    """
    seed = SEED_BASE + round_number
    move_rng = random.Random(seed)

    engine = ScopaEngine()
    cards = loadDeck("napolitane")
    state = engine.create_game(cards, PLAYER_IDS, seed=seed)
    total_moves = 0

    try:
        while not engine.is_round_over(state):
            # ── Deal if all hands are empty ───────────────────────────────────
            state = engine.deal_if_needed(state)

            # ── Select and submit move ────────────────────────────────────────
            card_id, capture_ids = _select_move(engine, state, move_rng)
            player_id = state.current_player.id
            state = engine.play_card(state, player_id, card_id, capture_ids)
            total_moves += 1

            # ── Post-move deal (explicit, per harness spec) ───────────────────
            state = engine.deal_if_needed(state)

        # ── Finalise round ────────────────────────────────────────────────────
        final = engine.calculate_round_score(state)

        # ── Invariant assertions ──────────────────────────────────────────────
        _assert_round_integrity(final)

        # ── Build result ──────────────────────────────────────────────────────
        scopas = {p.id: p.scopas for p in final.players}
        cards_captured = {p.id: len(p.captured) for p in final.players}
        coins_captured = {
            p.id: sum(1 for c in p.captured if c.suit == _COINS_SUIT)
            for p in final.players
        }
        settebello_winner = next(
            (
                p.id for p in final.players
                if any(
                    c.suit == _COINS_SUIT and c.value == _SETTEBELLO_VALUE
                    for c in p.captured
                )
            ),
            None,
        )
        primiera_scores = {p.id: _compute_primiera(p.captured) for p in final.players}

        return RoundResult(
            round_number=round_number,
            scores=dict(final.scores),
            scopas=scopas,
            cards_captured=cards_captured,
            coins_captured=coins_captured,
            settebello_winner=settebello_winner,
            primiera_winner=_strict_winner(primiera_scores),
            cards_winner=_strict_winner(cards_captured),
            coins_winner=_strict_winner(coins_captured),
            score_winner=_strict_winner(dict(final.scores)),
            total_moves=total_moves,
        )

    except (AssertionError, Exception) as exc:
        print(
            f"\n{'─' * 60}\n"
            f"  [ERROR] Round {round_number} failed — "
            f"{type(exc).__name__}: {exc}\n"
            f"  State snapshot at time of failure:\n"
            f"{_format_state_snapshot(state, round_number)}\n"
            f"{'─' * 60}"
        )
        raise


def _init_stats() -> SimStats:
    """Return a zeroed :class:`SimStats` pre-populated for all player IDs."""
    s = SimStats()
    for pid in PLAYER_IDS:
        s.cumulative_scores[pid] = 0
        s.cumulative_scopas[pid] = 0
        s.score_wins[pid]        = 0
        s.primiera_wins[pid]     = 0
        s.cards_wins[pid]        = 0
        s.coins_wins[pid]        = 0
        s.settebello_wins[pid]   = 0
    return s


def _accumulate_stats(stats: SimStats, result: RoundResult) -> None:
    """Fold one :class:`RoundResult` into *stats* (mutates *stats* in place)."""
    stats.total_rounds += 1
    stats.total_moves  += result.total_moves

    for pid in PLAYER_IDS:
        stats.cumulative_scores[pid] += result.scores.get(pid, 0)
        stats.cumulative_scopas[pid] += result.scopas.get(pid, 0)

    scopa_total_this_round = sum(result.scopas.values())
    stats.scopa_events_total += scopa_total_this_round
    if scopa_total_this_round > 0:
        stats.rounds_with_scopa += 1

    # Score winner / tie
    if result.score_winner:
        stats.score_wins[result.score_winner] += 1
    else:
        stats.score_ties += 1

    # Primiera winner / tie
    if result.primiera_winner:
        stats.primiera_wins[result.primiera_winner] += 1
    else:
        stats.primiera_ties += 1

    # Most cards winner / tie
    if result.cards_winner:
        stats.cards_wins[result.cards_winner] += 1
    else:
        stats.cards_ties += 1

    # Most coins winner / tie
    if result.coins_winner:
        stats.coins_wins[result.coins_winner] += 1
    else:
        stats.coins_ties += 1

    # Settebello (always exactly one winner)
    if result.settebello_winner:
        stats.settebello_wins[result.settebello_winner] += 1


def _pct(numerator: int, denominator: int) -> str:
    """Format a percentage string, safe against zero denominator."""
    if denominator == 0:
        return "—"
    return f"{numerator / denominator * 100:.1f}%"


def _print_summary(stats: SimStats) -> None:
    """Print the final aggregate statistics report to stdout."""
    n = stats.total_rounds
    w = 46  # column width for alignment

    def row(label: str, value: str) -> None:
        print(f"  {label:<{w - 2}} {value}")

    print()
    print("=" * w)
    print("  Simulation Complete")
    print("=" * w)
    row("Total rounds         :", str(n))
    row("Total moves          :", f"{stats.total_moves:,}  "
        f"(avg {stats.total_moves / n:.1f} / round)")
    print(f"  {'─' * (w - 2)}")

    for pid in PLAYER_IDS:
        avg = stats.cumulative_scores[pid] / n if n else 0
        row(
            f"{pid} total score        :",
            f"{stats.cumulative_scores[pid]:,}  (avg {avg:.2f} / round)",
        )
    print(f"  {'─' * (w - 2)}")

    for pid in PLAYER_IDS:
        wins = stats.score_wins[pid]
        row(f"{pid} score wins         :", f"{wins:>5}  ({_pct(wins, n)})")
    row("Score ties           :", f"{stats.score_ties:>5}  ({_pct(stats.score_ties, n)})")
    print(f"  {'─' * (w - 2)}")

    for pid in PLAYER_IDS:
        row(
            f"{pid} total scopas       :",
            str(stats.cumulative_scopas[pid]),
        )
    row(
        "Total scopa events   :",
        f"{stats.scopa_events_total}",
    )
    row(
        "Rounds with ≥1 scopa :",
        f"{stats.rounds_with_scopa:>5}  ({_pct(stats.rounds_with_scopa, n)})",
    )
    print(f"  {'─' * (w - 2)}")

    for pid in PLAYER_IDS:
        pw = stats.primiera_wins[pid]
        row(f"{pid} primiera wins      :", f"{pw:>5}  ({_pct(pw, n)})")
    row(
        "Primiera ties        :",
        f"{stats.primiera_ties:>5}  ({_pct(stats.primiera_ties, n)})",
    )
    print(f"  {'─' * (w - 2)}")

    for pid in PLAYER_IDS:
        sw = stats.settebello_wins[pid]
        row(f"{pid} settebello wins    :", f"{sw:>5}  ({_pct(sw, n)})")
    print(f"  {'─' * (w - 2)}")

    for pid in PLAYER_IDS:
        cw = stats.cards_wins[pid]
        row(f"{pid} most-cards wins    :", f"{cw:>5}  ({_pct(cw, n)})")
    row(
        "Most-cards ties      :",
        f"{stats.cards_ties:>5}  ({_pct(stats.cards_ties, n)})",
    )
    print(f"  {'─' * (w - 2)}")

    for pid in PLAYER_IDS:
        ow = stats.coins_wins[pid]
        row(f"{pid} most-coins wins    :", f"{ow:>5}  ({_pct(ow, n)})")
    row(
        "Most-coins ties      :",
        f"{stats.coins_ties:>5}  ({_pct(stats.coins_ties, n)})",
    )
    print(f"  {'─' * (w - 2)}")

    if stats.unexpected_errors == 0:
        row("Rule violations      :", "None detected ✓")
    else:
        row("Unexpected errors    :", f"{stats.unexpected_errors}  ← investigate")

    print("=" * w)


def run_simulation(rounds: int = SIMULATION_ROUNDS) -> None:
    """
    Execute *rounds* complete Scopa simulations and print aggregate statistics.

    Terminates immediately (fail-fast) on any unexpected exception, after
    printing the offending round number, a compact state snapshot, and the
    full Python traceback.

    Parameters
    ----------
    rounds:
        Number of rounds to simulate.  Defaults to ``SIMULATION_ROUNDS``.
    """
    stats = _init_stats()

    for r in range(1, rounds + 1):
        try:
            result = simulate_one_round(r)
            _accumulate_stats(stats, result)
            # Flush ensures real-time progress visibility
            print(f"Round {r:>{len(str(rounds))}} ✓", flush=True)
        except Exception:
            stats.unexpected_errors += 1
            traceback.print_exc()
            print(
                f"\nSimulation aborted at round {r} / {rounds}.",
                file=sys.stderr,
            )
            sys.exit(1)

    _print_summary(stats)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """Run the simulation from the command line."""
    run_simulation(SIMULATION_ROUNDS)


if __name__ == "__main__":
    main()
