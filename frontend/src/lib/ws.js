/**
 * src/lib/ws.js
 * =============
 * WebSocket client.  A single persistent connection per game session.
 *
 * Only the game page calls `connect()` / `disconnect()`.
 * Components call `sendPlay()` and `sendGetCaptures()` to submit actions.
 *
 * All incoming messages update Svelte stores — components never parse raw
 * WebSocket frames.
 */

import {
    gameState, wsStatus, roundResult, errorMessage,
    captureOptions, selectedCard, isWaiting, opponentId,
    isDealing, roundNumber, dealType, capturesLoaded, lastScopaBy,
} from './stores/game.js';

/** @type {WebSocket|null} */
let _ws = null;

/** Cached player ID so scopa detection doesn't need subscribe(). */
let _myPlayerId = null;

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Open a WebSocket connection for the given session + player.
 * Idempotent — closes any existing connection first.
 */
export function connect(sessionId, playerId) {
    _myPlayerId = playerId;
    if (_ws) {
        _ws.close();
        _ws = null;
    }

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url   = `${proto}//${location.host}/ws/${sessionId}/${playerId}`;

    wsStatus.set('connecting');
    _ws = new WebSocket(url);

    _ws.onopen = () => {
        wsStatus.set('connected');
        console.log('[WS] Connected to', url);
    };

    _ws.onmessage = ({ data }) => {
        try {
            _dispatch(JSON.parse(data));
        } catch (e) {
            console.error('[WS] Failed to parse message:', data, e);
        }
    };

    _ws.onerror = (err) => {
        console.error('[WS] Error:', err);
        wsStatus.set('disconnected');
    };

    _ws.onclose = () => {
        wsStatus.set('disconnected');
        console.log('[WS] Closed');
    };
}

/** Close the WebSocket connection. */
export function disconnect() {
    if (_ws) {
        _ws.close();
        _ws = null;
    }
}

/**
 * Submit a card play.
 * @param {string}   cardId
 * @param {string[]} captureIds  Empty array = discard.
 */
export function sendPlay(cardId, captureIds = []) {
    _send({ type: 'play', card_id: cardId, capture_ids: captureIds });
}

/**
 * Ask the server for all legal capture sets for a card.
 * The response arrives as a `captures` message.
 * @param {string} cardId
 */
export function sendGetCaptures(cardId) {
    _send({ type: 'get_captures', card_id: cardId });
}

// ── Message dispatch ──────────────────────────────────────────────────────────

function _dispatch(msg) {
    switch (msg.type) {

        case 'waiting':
            isWaiting.set(true);
            wsStatus .set('waiting');
            break;

        case 'game_started':
            isWaiting.set(false);
            wsStatus .set('connected');
            if (msg.opponent_id) opponentId.set(msg.opponent_id);
            if (msg.round)       roundNumber.set(msg.round);
            // Clear stale interaction state on every new round
            selectedCard  .set(null);
            captureOptions.set([]);
            capturesLoaded.set(false);
            roundResult   .set(null);
            gameState     .set(null);   // hide board while dealing
            dealType      .set('full'); // full 10-card deal animation
            isDealing     .set(true);   // trigger deal animation
            break;

        case 'cards_dealt':
            // Mid-round refill: both hands were empty, new hands dealt from deck.
            if (msg.round) roundNumber.set(msg.round);
            selectedCard  .set(null);
            captureOptions.set([]);
            capturesLoaded.set(false);
            dealType      .set('hands'); // 6-card hand-only animation
            isDealing     .set(true);
            break;

        case 'state': {
            // Detect scopa: compare scopas count against previous state
            let prev = null;
            gameState.subscribe(s => { prev = s; })();
            const newState = msg.state;
            if (prev) {
                for (const [pid, pinfo] of Object.entries(newState.players ?? {})) {
                    const oldScopas = prev.players?.[pid]?.scopas ?? 0;
                    if (pinfo.scopas > oldScopas) {
                        lastScopaBy.set({ player_id: pid, is_mine: pid === _myPlayerId });
                        setTimeout(() => lastScopaBy.set(null), 2500);
                    }
                }
            }
            gameState    .set(newState);
            errorMessage .set(null);
            roundResult  .set(null);
            // If it is no longer our turn, clear pending selections
            if (!newState.is_human_turn) {
                selectedCard  .set(null);
                captureOptions.set([]);
                capturesLoaded.set(false);
            }
            break;
        }

        case 'captures':
            captureOptions.set(msg.options);
            capturesLoaded.set(true);
            break;

        case 'round_over':
            roundResult   .set(msg);
            captureOptions.set([]);
            capturesLoaded.set(false);
            selectedCard  .set(null);
            break;

        case 'error':
            errorMessage.set(msg.message);
            setTimeout(() => errorMessage.set(null), 4000);
            break;

        case 'opponent_disconnected':
            wsStatus    .set('disconnected');
            errorMessage.set('Opponent disconnected.');
            break;

        case 'pong':
            break;

        default:
            console.warn('[WS] Unknown message type:', msg.type);
    }
}

// ── Internal ──────────────────────────────────────────────────────────────────

function _send(msg) {
    if (_ws && _ws.readyState === WebSocket.OPEN) {
        _ws.send(JSON.stringify(msg));
    } else {
        console.warn('[WS] Cannot send — not connected:', msg);
    }
}
