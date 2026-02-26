"""
src/multiplayer/router.py
=========================
FastAPI routers for the Scopa multiplayer backend.

REST
----
POST /api/session
    Create a new session.
    Response: ``{session_id, join_code, player_id}``

POST /api/session/join
    Join an existing session by join_code.
    Response: ``{session_id, player_id}``

WebSocket
---------
/ws/{session_id}/{player_id}

    Client → Server messages (JSON)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``{"type": "play",         "card_id": "…", "capture_ids": […]}``
    ``{"type": "get_captures", "card_id": "…"}``
    ``{"type": "ping"}``

    Server → Client messages (JSON)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``{"type": "waiting",              "message": "…"}``
    ``{"type": "game_started",         "your_id": "…", "opponent_id": "…", "round": n}``
    ``{"type": "state",                "state": {…public_state…}}``
    ``{"type": "captures",             "card_id": "…", "options": [[…], …]}``
    ``{"type": "round_over",           "round_scores": {…}, "cumulative": {…}, …}``
    ``{"type": "error",                "message": "…"}``
    ``{"type": "opponent_disconnected"}``
    ``{"type": "pong"}``

Design invariants
-----------------
* Server-authoritative only.  The client never computes game state.
* ``serialize_public_state`` is the sole serialisation path; the raw
  ``GameState`` is never sent over the wire.
* All rule exceptions (``ScopaEngineError`` subclasses) produce
  ``{"type": "error", "message": "…"}`` instead of crashing the socket.
* An asyncio lock per session serialises concurrent move submissions.
* ``get_captures`` is read-only and bypasses the lock.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.engine import ScopaEngineError

from .manager import manager
from .models import MultiplayerGameSession, MultiplayerSession

log = logging.getLogger(__name__)

rest_router = APIRouter()
ws_router   = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
#  Pydantic request / response models
# ─────────────────────────────────────────────────────────────────────────────

class CreateSessionResponse(BaseModel):
    session_id: str
    join_code:  str
    player_id:  str


class JoinRequest(BaseModel):
    join_code: str


class JoinResponse(BaseModel):
    session_id: str
    player_id:  str


# ─────────────────────────────────────────────────────────────────────────────
#  REST endpoints
# ─────────────────────────────────────────────────────────────────────────────

@rest_router.post("/session", response_model=CreateSessionResponse)
async def create_session() -> CreateSessionResponse:
    """Create a new session and return the join code + your player ID."""
    session, player_id = manager.create_session()
    return CreateSessionResponse(
        session_id=session.session_id,
        join_code=session.join_code,
        player_id=player_id,
    )


@rest_router.post("/session/join", response_model=JoinResponse)
async def join_session(body: JoinRequest) -> JoinResponse:
    """Join an existing session by its join code."""
    try:
        session, player_id = manager.join_session(body.join_code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return JoinResponse(session_id=session.session_id, player_id=player_id)


# ─────────────────────────────────────────────────────────────────────────────
#  WebSocket helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _send(ws: WebSocket, msg: dict[str, Any]) -> None:
    """Send a JSON message.  Swallows errors on dead/closing sockets."""
    try:
        await ws.send_json(msg)
    except Exception:
        pass


async def _broadcast(session: MultiplayerSession, msg: dict[str, Any]) -> None:
    """Send the same message to every connected player."""
    for ws in list(session.connections.values()):
        await _send(ws, msg)


async def _broadcast_state(session: MultiplayerSession) -> None:
    """
    Broadcast the current game state to both connected players.

    Each player receives a tailored snapshot — their own hand is visible,
    the opponent's is hidden.
    """
    game = session.game
    if game is None:
        return
    for pid, ws in list(session.connections.items()):
        state_dict = game.get_state_for_player(pid)
        await _send(ws, {"type": "state", "state": state_dict})


async def _start_game(session: MultiplayerSession) -> None:
    """Start round 1 and broadcast the initial state to both players."""
    session.game = MultiplayerGameSession(
        player_ids=list(session.player_ids),
        deck_name="napolitane",
    )
    session.status = "active"
    session.game.start_round()

    # Notify each player of their identity and their opponent's
    for pid, ws in list(session.connections.items()):
        await _send(ws, {
            "type":        "game_started",
            "your_id":     pid,
            "opponent_id": session.other_player_id(pid),
            "round":       session.game.round_number,
        })

    await _broadcast_state(session)


# ─────────────────────────────────────────────────────────────────────────────
#  WebSocket endpoint
# ─────────────────────────────────────────────────────────────────────────────

@ws_router.websocket("/ws/{session_id}/{player_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    player_id: str,
) -> None:
    # ── Validate session ──────────────────────────────────────────────────────
    try:
        session = manager.get_session(session_id)
    except KeyError:
        await websocket.close(code=4404)
        return

    if player_id not in session.player_ids:
        await websocket.close(code=4403)
        return

    await websocket.accept()

    # ── Register connection & handle initial state ────────────────────────────
    session.connections[player_id] = websocket

    if session.status == "abandoned":
        await _send(websocket, {"type": "opponent_disconnected"})

    elif session.status == "active" and session.game is not None:
        # Reconnect mid-game: re-sync the rejoining player
        await _send(websocket, {
            "type":        "game_started",
            "your_id":     player_id,
            "opponent_id": session.other_player_id(player_id),
            "round":       session.game.round_number,
        })
        state_dict = session.game.get_state_for_player(player_id)
        await _send(websocket, {"type": "state", "state": state_dict})

    elif len(session.connections) == 2 and session.status == "waiting":
        # Both players now connected → start the game
        await _start_game(session)

    else:
        # Waiting for the other player to connect
        await _send(websocket, {
            "type":    "waiting",
            "message": "Waiting for opponent to connect…",
        })

    # ── Message loop ──────────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _send(websocket, {"type": "error", "message": "Invalid JSON."})
                continue

            await _handle_message(session, player_id, websocket, msg)

    except WebSocketDisconnect:
        session.connections.pop(player_id, None)
        if session.status == "active":
            session.status = "abandoned"
            opponent_id = session.other_player_id(player_id)
            opp_ws = session.connections.get(opponent_id)
            if opp_ws:
                await _send(opp_ws, {"type": "opponent_disconnected"})
        log.info("Player %s disconnected from session %s", player_id, session_id)


# ─────────────────────────────────────────────────────────────────────────────
#  Message dispatcher
# ─────────────────────────────────────────────────────────────────────────────

async def _handle_message(
    session:   MultiplayerSession,
    player_id: str,
    websocket: WebSocket,
    msg:       dict,
) -> None:
    """Dispatch a single incoming WebSocket message."""

    if session.status != "active" or session.game is None:
        await _send(websocket, {"type": "error", "message": "Game is not active."})
        return

    game     = session.game
    msg_type = msg.get("type")

    # ── play ──────────────────────────────────────────────────────────────────
    if msg_type == "play":
        card_id     = str(msg.get("card_id", ""))
        capture_ids = list(msg.get("capture_ids", []))

        async with session._lock:
            try:
                cards_dealt = game.play_move(player_id, card_id, capture_ids)
            except ScopaEngineError as exc:
                await _send(websocket, {"type": "error", "message": str(exc)})
                return

            # If both hands were empty and new cards were drawn from the deck,
            # tell clients to play the hand-deal animation before showing state.
            if cards_dealt:
                await _broadcast(session, {
                    "type":  "cards_dealt",
                    "round": game.round_number,
                })

            await _broadcast_state(session)

            if game.is_round_over():
                result = game.finalize_round()
                await _broadcast(session, {"type": "round_over", **result})

                # Pause so both players can see the result, then auto-start next round
                await asyncio.sleep(4)
                game.start_round()
                await _broadcast(session, {
                    "type":  "game_started",
                    "round": game.round_number,
                })
                await _broadcast_state(session)

    # ── get_captures (read-only — no lock needed) ─────────────────────────────
    elif msg_type == "get_captures":
        card_id = str(msg.get("card_id", ""))
        try:
            options = game.get_legal_captures(player_id, card_id)
        except (KeyError, ScopaEngineError) as exc:
            await _send(websocket, {"type": "error", "message": str(exc)})
            return
        await _send(websocket, {
            "type":    "captures",
            "card_id": card_id,
            "options": options,
        })

    # ── ping ──────────────────────────────────────────────────────────────────
    elif msg_type == "ping":
        await _send(websocket, {"type": "pong"})

    else:
        await _send(websocket, {
            "type":    "error",
            "message": f"Unknown message type: {msg_type!r}",
        })
