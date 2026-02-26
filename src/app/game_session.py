"""
src/app/game_session.py
=======================
Application-layer orchestrator for one Human vs AI Scopa session.

Layer contract
--------------
``GameSession`` is the **only** object the UI / network layer ever touches.

* It never exposes raw ``GameState`` to callers — snapshots go through
  ``serialize_public_state`` first.
* It never mutates engine state directly — every change flows through
  ``ScopaEngine`` methods.
* Custom engine exceptions (``WrongTurnError``, ``InvalidCaptureError``,
  etc.) propagate upward unchanged so the caller can present descriptive
  messages without reimplementing rule logic.

Multi-round sessions
--------------------
``GameSession`` accumulates scores and round history across multiple rounds::

    session = GameSession(seed=42)

    for _ in range(best_of_3):
        session.start_round()
        while not session.is_round_over():
            if session.is_human_turn:
                session.play_human_move(card_id, capture_ids)
            else:
                session.play_ai_turn()
        result = session.get_final_scores()

    # session.cumulative_scores has the match totals.

Persistence
-----------
::

    snapshot = session.export()          # → JSON-ready dict
    restored = GameSession.from_snapshot(snapshot)   # → GameSession
"""

from __future__ import annotations

import random
from typing import Optional

import src.decks  # noqa: F401 — registers all deck definitions on first import

from src.engine import (
    GameConfig,
    GameState,
    ScopaEngine,
    ScopaEngineError,
    loadDeck,
)
from src.engine.scopa import WrongTurnError

from .ai_player import AIStrategy, SimpleAI
from .serializer import (
    deserialize_game_state,
    export_game_state,
    serialize_public_state,
)


class GameSession:
    """
    Single-match orchestrator for one Human vs AI Scopa session.

    The human player is always ``player_ids[0]``; the AI is ``player_ids[1]``.

    Parameters
    ----------
    player_ids:
        Ordered ``[human_id, ai_id]``.  Defaults to ``["human", "ai"]``.
    deck_name:
        Registered deck to play with.  Defaults to ``"napolitane"``.
    seed:
        Master RNG seed.  Round *n* uses ``seed + n`` for both the deck
        shuffle and the AI's move RNG, so every session is fully
        reproducible.  Pass ``None`` for non-deterministic play.
    config:
        Optional ``GameConfig`` override (hand size, table size, …).
    ai_strategy:
        AI implementation.  Defaults to ``SimpleAI()``.  Swap for a
        stronger strategy without changing any other code.
    """

    DEFAULT_HUMAN_ID: str = "human"
    DEFAULT_AI_ID:    str = "ai"

    def __init__(
        self,
        player_ids:  Optional[list[str]] = None,
        deck_name:   str = "napolitane",
        seed:        Optional[int] = None,
        config:      Optional[GameConfig] = None,
        ai_strategy: Optional[AIStrategy] = None,
    ) -> None:
        self.player_ids:  list[str]            = player_ids or [self.DEFAULT_HUMAN_ID, self.DEFAULT_AI_ID]
        self.human_id:    str                  = self.player_ids[0]
        self.ai_id:       str                  = self.player_ids[1]
        self.deck_name:   str                  = deck_name
        self.seed:        Optional[int]        = seed
        self.config:      Optional[GameConfig] = config

        self._engine:       ScopaEngine         = ScopaEngine()
        self._ai:           AIStrategy          = ai_strategy or SimpleAI()
        self._state:        Optional[GameState] = None
        self._ai_rng:       random.Random       = random.Random(seed)
        self._round_number: int                 = 0

        self.cumulative_scores: dict[str, int] = {pid: 0 for pid in self.player_ids}
        self.round_history:     list[dict]     = []

    # ── Round lifecycle ───────────────────────────────────────────────────────

    def start_round(self) -> None:
        """
        Load a fresh deck, shuffle it, deal initial cards, and begin play.

        Increments the internal round counter.  Can be called repeatedly to
        start successive rounds in the same session.
        """
        self._round_number += 1
        round_seed = (self.seed + self._round_number) if self.seed is not None else None
        self._ai_rng = random.Random(round_seed)

        cards       = loadDeck(self.deck_name)
        self._state = self._engine.create_game(
            cards,
            self.player_ids,
            config=self.config,
            seed=round_seed,
        )

    # ── Move submission ───────────────────────────────────────────────────────

    def play_human_move(self, card_id: str, capture_ids: list[str]) -> None:
        """
        Submit the human player's chosen move.

        The engine performs full validation before applying any state change.
        All rule violations surface as typed ``ScopaEngineError`` subclasses
        which the caller should catch and present to the user.

        After a successful move, ``deal_if_needed`` is called automatically.

        Parameters
        ----------
        card_id:
            ``Card.id`` of the card to play from the human's hand.
        capture_ids:
            ``Card.id`` list of the table cards to capture.
            Pass ``[]`` to discard (place the card on the table).

        Raises
        ------
        ScopaEngineError
            If no round is active (``start_round`` not yet called).
        WrongTurnError
            If it is not the human's turn.
        CardNotInHandError
            If ``card_id`` is not in the human's hand.
        InvalidCaptureError
            If the capture set is illegal (wrong sum, card not on table).
        EqualValuePriorityError
            If an exact-value match must be captured instead of a sum combo.
        """
        self._require_active()
        self._state = self._engine.play_card(
            self._state, self.human_id, card_id, capture_ids
        )
        self._state = self._engine.deal_if_needed(self._state)

    def play_ai_turn(self) -> tuple[str, list[str]]:
        """
        Let the AI select and execute its move.

        Returns
        -------
        (card_id, capture_ids)
            The move the AI played.  The UI can use this to animate the
            action (slide card from hand to table / capture pile).

        Raises
        ------
        ScopaEngineError
            If no round is active.
        WrongTurnError
            If it is not the AI's turn.
        """
        self._require_active()
        if self._state.current_player.id != self.ai_id:
            raise WrongTurnError(
                acting=self.ai_id,
                expected=self._state.current_player.id,
            )

        card_id, capture_ids = self._ai.choose_move(
            self._engine, self._state, self.ai_id, self._ai_rng
        )
        self._state = self._engine.play_card(
            self._state, self.ai_id, card_id, capture_ids
        )
        self._state = self._engine.deal_if_needed(self._state)
        return card_id, capture_ids

    # ── Query helpers ─────────────────────────────────────────────────────────

    def get_public_state(self) -> dict:
        """
        Return a UI-safe state snapshot (see :func:`serialize_public_state`).

        Strips: opponent hand cards, deck order.
        Includes: human hand, table, captured counts, deck size, turn info.
        """
        self._require_active()
        return serialize_public_state(self._state, self.human_id)

    def get_legal_captures(self, card_id: str) -> list[list[str]]:
        """
        Enumerate all legal capture sets for a card in the human's hand.

        Returns a list of ``card_id`` lists.  Each inner list is one valid
        capture option to pass directly to ``play_human_move``.  An empty
        outer list means the card can only be discarded.

        This is a **pure query** — it does not mutate state.

        Parameters
        ----------
        card_id:
            ``Card.id`` of a card currently in the human's hand.

        Raises
        ------
        ScopaEngineError
            If no round is active.
        KeyError
            If *card_id* is not in the human's hand.
        """
        self._require_active()
        human = self._state.player_by_id(self.human_id)
        card  = next((c for c in human.hand if c.id == card_id), None)
        if card is None:
            raise KeyError(f"Card '{card_id}' is not in the human's hand.")
        combos = self._engine._find_sum_combinations(card.value, self._state.table)
        return [[c.id for c in combo] for combo in combos]

    def is_round_over(self) -> bool:
        """Return ``True`` when the deck and all hands are empty."""
        return (
            self._state is not None
            and self._engine.is_round_over(self._state)
        )

    def get_final_scores(self) -> dict:
        """
        Finalise the round: award table remainder, compute all scoring
        categories, update cumulative totals, archive the round.

        Call exactly once after ``is_round_over()`` returns ``True``.

        Returns
        -------
        dict
            ``{round_scores, cumulative, round_number, scopas}``
        """
        self._require_active()
        self._state = self._engine.calculate_round_score(self._state)

        round_scores: dict[str, int] = dict(self._state.scores)
        for pid, pts in round_scores.items():
            self.cumulative_scores[pid] += pts

        entry = {
            "round_number": self._round_number,
            "round_scores": round_scores,
            "scopas":       {p.id: p.scopas for p in self._state.players},
        }
        self.round_history.append(entry)

        return {
            "round_scores":  round_scores,
            "cumulative":    dict(self.cumulative_scores),
            "round_number":  self._round_number,
            "scopas":        entry["scopas"],
        }

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def current_player_id(self) -> Optional[str]:
        """ID of the player whose turn it is, or ``None`` before ``start_round``."""
        return self._state.current_player.id if self._state else None

    @property
    def round_number(self) -> int:
        """Current round counter (0 before the first ``start_round`` call)."""
        return self._round_number

    @property
    def is_human_turn(self) -> bool:
        """``True`` when it is currently the human player's turn."""
        return self.current_player_id == self.human_id

    # ── Persistence ───────────────────────────────────────────────────────────

    def export(self) -> dict:
        """
        Serialise the full session to a JSON-ready ``dict``.

        Round-trips through ``GameSession.from_snapshot``::

            snapshot = session.export()
            restored = GameSession.from_snapshot(snapshot)
            # `restored` resumes from exactly the same state.
        """
        return export_game_state(self)

    @classmethod
    def from_snapshot(cls, data: dict) -> GameSession:
        """
        Restore a ``GameSession`` from a snapshot produced by ``export()``.

        Parameters
        ----------
        data:
            JSON-parsed ``dict`` from a previous ``export()`` call.

        Returns
        -------
        GameSession
            Fully restored session, ready to resume play.
        """
        session = cls(
            player_ids=list(data["player_ids"]),
            deck_name=data["deck_name"],
            seed=data.get("seed"),
        )
        session._round_number     = int(data["round_number"])
        session.cumulative_scores = {k: int(v) for k, v in data["cumulative_scores"].items()}
        session.round_history     = list(data["round_history"])

        if data.get("current_state") is not None:
            session._state = deserialize_game_state(data["current_state"])

        return session

    # ── Internal ──────────────────────────────────────────────────────────────

    def _require_active(self) -> None:
        if self._state is None:
            raise ScopaEngineError(
                "No active round.  Call start_round() first."
            )
