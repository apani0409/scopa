"""
src/multiplayer/models.py
=========================
Core data models for the multiplayer layer.

``MultiplayerGameSession``
    Wraps ``ScopaEngine`` for games between two human players (no AI).
    Both players submit moves through ``play_move()``.
    Image URLs are rewritten to ``/assets/napolitane/…`` so the SvelteKit
    frontend can serve them as static files.

``MultiplayerSession``
    WebSocket session record: two player IDs, their live connections,
    the game instance, and an asyncio lock to serialise concurrent moves.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

import src.decks  # noqa: F401 — registers all deck definitions on import

from src.engine import Card, ScopaEngine, ScopaEngineError, loadDeck
from src.engine.scopa import GameState
from src.app.serializer import serialize_public_state


# ─────────────────────────────────────────────────────────────────────────────
#  MultiplayerGameSession
# ─────────────────────────────────────────────────────────────────────────────

class MultiplayerGameSession:
    """
    ScopaEngine wrapper for 2-human multiplayer games.

    Unlike ``GameSession`` (Human vs AI), this class manages two human
    players.  No AI is involved.  Both players submit moves through
    ``play_move()``.

    Card image URLs are rewritten from filesystem paths to web-friendly
    ``/assets/napolitane/{suit}/{value}_{suit}.png`` paths that the
    SvelteKit frontend serves from its ``/static/assets/`` directory.
    """

    def __init__(
        self,
        player_ids: list[str],
        deck_name: str = "napolitane",
        seed: Optional[int] = None,
    ) -> None:
        if len(player_ids) != 2:
            raise ValueError("MultiplayerGameSession requires exactly 2 player IDs.")
        self.player_ids = player_ids
        self.deck_name = deck_name
        self.seed = seed
        self._engine = ScopaEngine()
        self._state: Optional[GameState] = None
        self._round_number = 0
        self._first_player_index = 0          # alternates each round
        self.cumulative_scores: dict[str, int] = {pid: 0 for pid in player_ids}
        self.round_history: list[dict] = []

    # ── Round lifecycle ───────────────────────────────────────────────────────

    def start_round(self) -> None:
        """Load a fresh deck, shuffle it, deal initial cards, and begin play."""
        self._round_number += 1
        round_seed = (self.seed + self._round_number) if self.seed is not None else None
        # Rotate player list so the starting player alternates each round
        rotated_ids = (
            self.player_ids[self._first_player_index:] +
            self.player_ids[:self._first_player_index]
        )
        cards = self._load_web_cards()
        self._state = self._engine.create_game(
            cards,
            rotated_ids,
            seed=round_seed,
        )
        # Next round the other player starts
        self._first_player_index = (self._first_player_index + 1) % len(self.player_ids)

    def _load_web_cards(self) -> list[Card]:
        """
        Load the deck and remap image URLs to frontend-served static paths.

        Converts filesystem URLs to ``/assets/napolitane/{suit}/{value}_{suit}.png``
        so the SvelteKit frontend can serve them from ``/static/assets/``.
        """
        raw = loadDeck(self.deck_name)
        return [
            Card(
                suit=c.suit,
                value=c.value,
                id=c.id,
                image_url=f"/assets/napolitane/{c.suit}/{c.value}_{c.suit}.png",
            )
            for c in raw
        ]

    # ── Moves ─────────────────────────────────────────────────────────────────

    def play_move(
        self,
        player_id: str,
        card_id: str,
        capture_ids: list[str],
    ) -> bool:
        """
        Execute a player's move and deal new cards if both hands are empty.

        Returns ``True`` if a mid-round deal occurred (both hands were empty
        and new cards were dealt from the deck).  The caller can use this to
        broadcast a ``cards_dealt`` notification before sending the new state.

        Raises ``ScopaEngineError`` subclasses on any rule violation so the
        WebSocket handler can send structured error messages.
        """
        self._require_active()
        self._state = self._engine.play_card(
            self._state, player_id, card_id, capture_ids
        )
        # Detect whether deal_if_needed will actually deal cards.
        needs_deal = (
            bool(self._state.deck)
            and all(len(p.hand) == 0 for p in self._state.players)
        )
        self._state = self._engine.deal_if_needed(self._state)
        return needs_deal

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_legal_captures(
        self, player_id: str, card_id: str
    ) -> list[list[str]]:
        """
        Return all legal capture sets for *card_id* in *player_id*'s hand.

        Each inner list is one valid ``capture_ids`` argument to pass to
        ``play_move``.  An empty outer list means the card can only be
        discarded.
        """
        self._require_active()
        player = self._state.player_by_id(player_id)
        card = next((c for c in player.hand if c.id == card_id), None)
        if card is None:
            raise KeyError(f"Card '{card_id}' not in player '{player_id}' hand.")
        combos = self._engine._find_sum_combinations(card.value, self._state.table)
        return [[c.id for c in combo] for combo in combos]

    def get_state_for_player(self, player_id: str) -> dict:
        """
        Return a UI-safe public state snapshot from *player_id*'s perspective.

        Hides the opponent's hand.  Uses ``serialize_public_state`` internally.
        """
        self._require_active()
        return serialize_public_state(self._state, player_id)

    def is_round_over(self) -> bool:
        """Return ``True`` when the deck and all hands are empty."""
        return self._state is not None and self._engine.is_round_over(self._state)

    @property
    def current_player_id(self) -> Optional[str]:
        return self._state.current_player.id if self._state else None

    @property
    def round_number(self) -> int:
        return self._round_number

    # ── Scoring ───────────────────────────────────────────────────────────────

    def finalize_round(self) -> dict:
        """
        Score the current round and update cumulative totals.

        Call exactly once after ``is_round_over()`` returns ``True``.

        Returns
        -------
        dict
            ``{round_scores, cumulative, round_number, scopas}``
        """
        self._require_active()
        self._state = self._engine.calculate_round_score(self._state)
        round_scores = dict(self._state.scores)
        for pid, pts in round_scores.items():
            self.cumulative_scores[pid] += pts
        entry = {
            "round_number": self._round_number,
            "round_scores": round_scores,
            "scopas": {p.id: p.scopas for p in self._state.players},
        }
        self.round_history.append(entry)
        return {
            "round_scores": round_scores,
            "cumulative":   dict(self.cumulative_scores),
            "round_number": self._round_number,
            "scopas":       entry["scopas"],
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _require_active(self) -> None:
        if self._state is None:
            raise ScopaEngineError("No active round.  Call start_round() first.")


# ─────────────────────────────────────────────────────────────────────────────
#  MultiplayerSession
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MultiplayerSession:
    """
    WebSocket session record.

    Holds two player IDs, their live WebSocket connections, the
    ``MultiplayerGameSession`` instance, and an asyncio lock to serialise
    concurrent move submissions.

    Status values
    -------------
    ``"waiting"``   — session created, waiting for 2nd player to connect
    ``"active"``    — both connected, game in progress
    ``"finished"``  — all rounds complete (reserved for future use)
    ``"abandoned"`` — a player disconnected mid-game
    """

    session_id: str
    join_code:  str
    player_ids: list[str]                          # [creator_id, joiner_id]
    game:       Optional[MultiplayerGameSession] = None
    status:     str                              = "waiting"
    created_at: float                            = field(default_factory=time.time)

    # player_id → fastapi.WebSocket (typed as Any to avoid circular import)
    connections: dict                            = field(default_factory=dict)

    # Serialises concurrent moves — one lock per session
    _lock: asyncio.Lock                          = field(default_factory=asyncio.Lock)

    def is_full(self) -> bool:
        """Return ``True`` when both player slots are filled."""
        return len(self.player_ids) == 2

    def both_connected(self) -> bool:
        """Return ``True`` when both players have an active WebSocket."""
        return len(self.connections) == 2

    def other_player_id(self, player_id: str) -> str:
        """Return the opponent's player ID."""
        for pid in self.player_ids:
            if pid != player_id:
                return pid
        raise ValueError(f"Player {player_id!r} not in session.")
