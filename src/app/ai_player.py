"""
src/app/ai_player.py
====================
AI opponent strategy framework for the Scopa game.

Architecture
------------
``AIStrategy`` is an abstract base class that defines the single method all
AI implementations must satisfy.  The only dependency injected at call-time
is the ``ScopaEngine`` instance (for legal-move enumeration) and a seeded
``random.Random`` (for tie-breaking).

This design means swapping strategies requires one constructor argument:

    session = GameSession(ai_strategy=MinimaxAI(depth=4))

Implemented strategies
-----------------------
``SimpleAI``
    Single-ply greedy strategy.  Enumerates all legal captures and ranks
    them by a fixed priority function.  No look-ahead.  Beats a random
    player decisively while remaining fast enough for real-time play.

    Priority order (highest first):
    1. Clears the table → scopa opportunity
    2. Most cards captured in one move
    3. Captures the settebello (7 of oro)
    4. Captures any oro card
    5. Highest played-card value (preserve low cards for future combos)
    6. Seeded RNG tie-break (deterministic)

    Discard policy (no captures possible):
    Prefer lowest-value non-oro card; fall back to oro if hand is all-oro.

Extensibility
-------------
To add Minimax / MCTS, subclass ``AIStrategy``, override ``choose_move``,
and inject via ``GameSession(ai_strategy=...)``.  Nothing else changes.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

from src.engine import Card, GameState, ScopaEngine


# ════════════════════════════════════════════════════════════════════════════
#  Abstract base
# ════════════════════════════════════════════════════════════════════════════

class AIStrategy(ABC):
    """
    Contract for all AI move-selection strategies.

    Parameters injected at each call
    ---------------------------------
    engine:
        The active ``ScopaEngine`` — used **read-only** for legal-move
        enumeration via ``_find_sum_combinations``.  Never mutated.
    state:
        Full current ``GameState``.  The AI may read any field.
    player_id:
        The AI's own player id in this state.
    rng:
        Seeded ``random.Random`` provided by the session.  All randomness
        must flow through this object so results are reproducible.
    """

    @abstractmethod
    def choose_move(
        self,
        engine: ScopaEngine,
        state: GameState,
        player_id: str,
        rng: random.Random,
    ) -> tuple[str, list[str]]:
        """
        Return ``(card_id, capture_ids)`` for the next move.

        ``capture_ids`` must be an empty list for a discard move.
        The returned move is still validated by the engine — the strategy
        must only return legal moves.
        """
        ...


# ════════════════════════════════════════════════════════════════════════════
#  Simple greedy AI
# ════════════════════════════════════════════════════════════════════════════

class SimpleAI(AIStrategy):
    """
    Single-ply greedy AI.  See module docstring for full strategy spec.
    """

    _COINS_SUIT: str = "oro"
    _SETTEBELLO:  int = 7

    def choose_move(
        self,
        engine: ScopaEngine,
        state: GameState,
        player_id: str,
        rng: random.Random,
    ) -> tuple[str, list[str]]:
        player = state.player_by_id(player_id)

        # ── Enumerate every legal (card, combo) pair ──────────────────────────
        all_moves: list[tuple[Card, list[Card]]] = [
            (card, combo)
            for card in player.hand
            for combo in engine._find_sum_combinations(card.value, state.table)
        ]

        if not all_moves:
            discard = self._choose_discard(player.hand, rng)
            return discard.id, []

        # ── Select best move(s), break ties with seeded RNG ───────────────────
        table_size = len(state.table)
        top_score  = max(self._score(card, combo, table_size) for card, combo in all_moves)
        candidates = [
            (card, combo)
            for card, combo in all_moves
            if self._score(card, combo, table_size) == top_score
        ]
        card, combo = rng.choice(candidates)
        return card.id, [c.id for c in combo]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _score(
        self,
        card: Card,
        combo: list[Card],
        table_size: int,
    ) -> tuple:
        """
        Return a comparable score tuple.  Larger = better.

        Tuple layout maps 1-to-1 with the priority list in the module docstring:
        (is_scopa, cards_taken, takes_settebello, takes_oro, played_value)
        """
        return (
            len(combo) == table_size,                                           # 1. scopa
            len(combo),                                                          # 2. most cards
            any(c.suit == self._COINS_SUIT and c.value == self._SETTEBELLO
                for c in combo),                                                 # 3. settebello
            any(c.suit == self._COINS_SUIT for c in combo),                     # 4. any oro
            card.value,                                                          # 5. high played value
        )

    def _choose_discard(
        self,
        hand: list[Card],
        rng: random.Random,
    ) -> Card:
        """
        Return the card to discard when no capture is possible.

        Strategy: discard the lowest-value non-oro card; if the hand is
        entirely oro, discard the lowest oro.
        """
        non_oro = [c for c in hand if c.suit != self._COINS_SUIT]
        pool    = non_oro if non_oro else hand
        min_val = min(c.value for c in pool)
        return rng.choice([c for c in pool if c.value == min_val])
