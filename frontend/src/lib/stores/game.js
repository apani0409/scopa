/**
 * src/lib/stores/game.js
 * ======================
 * Svelte stores that hold the entire client-side game state.
 *
 * Only `ws.js` writes to these stores (via the WebSocket dispatch loop).
 * UI components read them reactively and call `ws.js` functions to send moves.
 */

import { writable, derived } from 'svelte/store';

// ── Identity ──────────────────────────────────────────────────────────────────
export const sessionId  = writable(null);  // string | null
export const playerId   = writable(null);  // string | null  (our player ID)
export const opponentId = writable(null);  // string | null
export const joinCode   = writable(null);  // string | null  (creator only)

// ── Connection ────────────────────────────────────────────────────────────────
// 'disconnected' | 'connecting' | 'connected' | 'waiting'
export const wsStatus = writable('disconnected');

// ── Game state (from server serialize_public_state) ───────────────────────────
export const gameState = writable(null);

// ── Interaction ───────────────────────────────────────────────────────────────
export const selectedCard   = writable(null);   // full card object | null
export const captureOptions = writable([]);      // list<list<card_id>>
export const roundResult    = writable(null);    // round_over payload | null
export const errorMessage   = writable(null);    // string | null

// ── Waiting for opponent to connect ───────────────────────────────────────────
export const isWaiting  = writable(false);

// ── Deal animation ────────────────────────────────────────────────────────────
export const isDealing      = writable(false);   // true while dealing animation plays
export const roundNumber    = writable(1);       // current round number
export const dealType       = writable('full');  // 'full' (round start) | 'hands' (mid-round refill)
export const capturesLoaded = writable(false);   // true once server has responded to get_captures
export const lastScopaBy   = writable(null);     // null | { player_id, is_mine } — cleared after 2.5 s

// ── Derived convenience ───────────────────────────────────────────────────────
export const isMyTurn = derived(
    [gameState],
    ([$gs]) => $gs?.is_human_turn ?? false,
);

export const myHand = derived(
    [gameState],
    ([$gs]) => $gs?.human_hand ?? [],
);

export const tableCards = derived(
    [gameState],
    ([$gs]) => $gs?.table ?? [],
);

export const deckRemaining = derived(
    [gameState],
    ([$gs]) => $gs?.deck_remaining ?? 0,
);

export const scores = derived(
    [gameState],
    ([$gs]) => $gs?.scores ?? {},
);
