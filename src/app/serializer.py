"""
src/app/serializer.py
=====================
Serialization utilities for the Scopa application layer.

Three serialization tiers
--------------------------
1. **Public state** (``serialize_public_state``)
   UI-safe snapshot for one player.  Hides opponent hand and deck order.
   Safe to transmit over a network or WebSocket to the human client.

2. **Full game state** (``serialize_game_state`` / ``deserialize_game_state``)
   Lossless, round-trip-safe encoding of a complete ``GameState``.
   Used internally for persistence, replay, and session restore.

3. **Session snapshot** (``export_game_state`` / ``load_game_state``)
   Wraps the full state with session-level metadata (round history,
   cumulative scores, player IDs).  The top-level persistence format.

Notes
-----
* ``Card.image_url`` is preserved so the rendering layer can resume without
  re-resolving asset paths after a restore.
* ``GameConfig`` is intentionally **not** persisted.  A fresh ``GameConfig()``
  is applied on deserialise.  Add a ``_serialize_config`` pair here if
  custom configs ever need to be stored.
* All output values are primitive (``dict``, ``list``, ``str``, ``int``,
  ``None``) — JSON-serialisable without a custom encoder.
* No circular imports: this module only imports from ``src.engine``.
  ``load_game_state`` uses a lazy local import to reach ``GameSession`` in
  ``game_session.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from src.engine import Card
from src.engine.scopa import GameConfig, GameState, PlayerState

if TYPE_CHECKING:
    from .game_session import GameSession  # type-hints only, no runtime import

_SNAPSHOT_VERSION = "1.0"


# ════════════════════════════════════════════════════════════════════════════
#  Card
# ════════════════════════════════════════════════════════════════════════════

def _serialize_card(card: Card) -> dict[str, Any]:
    return {
        "id":        card.id,
        "suit":      card.suit,
        "value":     card.value,
        "image_url": card.image_url,
    }


def _deserialize_card(data: dict[str, Any]) -> Card:
    return Card(
        id=data["id"],
        suit=data["suit"],
        value=int(data["value"]),
        image_url=data.get("image_url", ""),
    )


# ════════════════════════════════════════════════════════════════════════════
#  Player
# ════════════════════════════════════════════════════════════════════════════

def _serialize_player(player: PlayerState) -> dict[str, Any]:
    return {
        "id":       player.id,
        "hand":     [_serialize_card(c) for c in player.hand],
        "captured": [_serialize_card(c) for c in player.captured],
        "scopas":   player.scopas,
    }


def _deserialize_player(data: dict[str, Any]) -> PlayerState:
    return PlayerState(
        id=data["id"],
        hand=[_deserialize_card(c) for c in data["hand"]],
        captured=[_deserialize_card(c) for c in data["captured"]],
        scopas=int(data["scopas"]),
    )


# ════════════════════════════════════════════════════════════════════════════
#  Full game state (lossless)
# ════════════════════════════════════════════════════════════════════════════

def serialize_game_state(state: GameState) -> dict[str, Any]:
    """
    Produce a lossless, JSON-serialisable encoding of *state*.

    ``GameConfig`` is omitted — defaults are reapplied on
    ``deserialize_game_state``.  See module docstring for rationale.
    """
    return {
        "deck":                    [_serialize_card(c) for c in state.deck],
        "table":                   [_serialize_card(c) for c in state.table],
        "players":                 [_serialize_player(p) for p in state.players],
        "current_player_index":    state.current_player_index,
        "last_capture_player_id":  state.last_capture_player_id,
        "scores":                  dict(state.scores),
        "phase":                   state.phase,
    }


def deserialize_game_state(data: dict[str, Any]) -> GameState:
    """
    Reconstruct a ``GameState`` from its serialised form.

    A fresh ``GameConfig()`` is applied.  Extend this function if custom
    configs need to be round-tripped.
    """
    return GameState(
        deck=                   [_deserialize_card(c) for c in data["deck"]],
        table=                  [_deserialize_card(c) for c in data["table"]],
        players=                [_deserialize_player(p) for p in data["players"]],
        current_player_index=   int(data["current_player_index"]),
        last_capture_player_id= data["last_capture_player_id"],
        scores=                 {k: int(v) for k, v in data["scores"].items()},
        phase=                  data["phase"],
        config=                 GameConfig(),
    )


# ════════════════════════════════════════════════════════════════════════════
#  Public state (UI-safe snapshot)
# ════════════════════════════════════════════════════════════════════════════

def serialize_public_state(
    state: GameState,
    human_player_id: str,
) -> dict[str, Any]:
    """
    Return a UI-safe snapshot for *human_player_id*.

    Hidden
    ------
    * Opponent's hand cards  (only count exposed).
    * Deck contents and order  (only remaining count exposed).

    Exposed
    -------
    * Human's full hand with all card fields (including ``image_url``).
    * All table cards with all fields.
    * Per-player summary: ``captured_count``, ``hand_count``, ``scopas``.
    * Current scores, phase, whose turn it is.
    * ``is_human_turn`` flag for simple UI branching.
    """
    human = state.player_by_id(human_player_id)
    # During a round state.scores is always {pid: 0} until calculate_round_score
    # is called at round end. Show live scopas count so the scoreboard reflects
    # scopas immediately as they happen.
    live_scores = {
        p.id: state.scores.get(p.id, 0) + p.scopas
        for p in state.players
    }
    return {
        "phase":                  state.phase,
        "deck_remaining":         len(state.deck),
        "table":                  [_serialize_card(c) for c in state.table],
        "human_hand":             [_serialize_card(c) for c in human.hand],
        "current_player_id":      state.current_player.id,
        "is_human_turn":          state.current_player.id == human_player_id,
        "last_capture_player_id": state.last_capture_player_id,
        "scores":                 live_scores,
        "players": {
            p.id: {
                "captured_count": len(p.captured),
                "hand_count":     len(p.hand),
                "scopas":         p.scopas,
            }
            for p in state.players
        },
    }


# ════════════════════════════════════════════════════════════════════════════
#  Session export / restore
# ════════════════════════════════════════════════════════════════════════════

def export_game_state(session: Any) -> dict[str, Any]:
    """
    Serialise a ``GameSession`` to a fully JSON-ready ``dict``.

    The *session* parameter is typed as ``Any`` to avoid a runtime circular
    import; it is expected to be a ``GameSession`` instance.

    Suitable for:

    * Saving to disk  — ``json.dump(export_game_state(session), fp)``
    * HTTP response   — ``json.dumps(export_game_state(session))``
    * Key-value store — ``redis.set(key, json.dumps(...))``
    """
    return {
        "version":           _SNAPSHOT_VERSION,
        "player_ids":        list(session.player_ids),
        "deck_name":         session.deck_name,
        "seed":              session.seed,
        "round_number":      session.round_number,
        "cumulative_scores": dict(session.cumulative_scores),
        "round_history":     list(session.round_history),
        "current_state": (
            serialize_game_state(session._state)
            if session._state is not None
            else None
        ),
    }


def load_game_state(data: dict[str, Any]) -> GameSession:
    """
    Reconstruct a ``GameSession`` from a snapshot produced by
    ``export_game_state``.

    Supports snapshots at any phase — ``"playing"``, ``"finished"``, or
    before the first ``start_round()`` call (``current_state`` is ``None``).

    Parameters
    ----------
    data:
        JSON-parsed ``dict`` from a previous ``export_game_state`` call.

    Returns
    -------
    GameSession
        Fully restored session, ready to resume play.
    """
    from .game_session import GameSession  # lazy import — breaks circular dep

    session = GameSession(
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
