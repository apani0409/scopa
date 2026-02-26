<!--
    GameBoard.svelte
    ================
    Main game UI layout.

    Regions (top → bottom)
    -----------------------
    1. Opponent area   — card backs, stats, turn indicator
    2. Table           — face-up community cards (clickable when capturing)
    3. Error banner    — dismissed automatically after 4 s
    4. Round result    — overlay shown until the next round starts
    5. Player hand     — your face-up cards (selectable on your turn)
    6. Action bar      — capture options + discard button

    Interaction model
    -----------------
    * Click a hand card → `sendGetCaptures` → server replies with options
    * Click a table card → pick the first capture option containing it
    * If multiple options match: action bar shows per-option buttons
    * Click "Discard" → `sendPlay(cardId, [])`
    * All game logic lives on the server.  This file never computes rules.
-->
<script>
    import Card     from './Card.svelte';
    import CardBack from './CardBack.svelte';
    import {
        gameState, selectedCard, captureOptions, capturesLoaded, lastScopaBy,
        isMyTurn, myHand, tableCards, scores, roundResult,
        playerId, opponentId, errorMessage,
    } from '$lib/stores/game.js';
    import { sendPlay, sendGetCaptures } from '$lib/ws.js';

    // ── Capture state ─────────────────────────────────────────────────────────

    /** Flat set of all card IDs that appear in any capture option. */
    $: capturableIds = new Set($captureOptions.flat());

    /**
     * Table cards tapped so far for a multi-card sum combination.
     * When this set exactly matches one capture option → play is executed.
     */
    let pendingTableIds = new Set();

    // Clear pending selection whenever the selected hand card is cleared
    $: if ($selectedCard === null) pendingTableIds = new Set();

    // ── Event handlers ────────────────────────────────────────────────────────

    function handleHandCard(card) {
        if (!$isMyTurn) return;

        if ($selectedCard?.id === card.id) {
            // Second tap on the same card.
            // If no captures are known yet or confirmed empty → try to discard.
            // The server will reject if a capture was actually mandatory.
            // If captures ARE available → deselect so the player can pick a different card.
            if ($captureOptions.length === 0) {
                executePlay(card.id, []);
            } else {
                cancelSelection();
            }
            return;
        }

        selectedCard  .set(card);
        captureOptions.set([]);
        capturesLoaded.set(false);
        pendingTableIds = new Set();
        sendGetCaptures(card.id);
    }

    function handleTableCard(card) {
        if (!$selectedCard || !$isMyTurn) return;
        if (!capturableIds.has(card.id) && !pendingTableIds.has(card.id)) return;

        // Toggle this card in the pending set
        const next = new Set(pendingTableIds);
        if (next.has(card.id)) {
            next.delete(card.id);
        } else {
            next.add(card.id);
        }
        pendingTableIds = next;

        // Check if pending set exactly matches one capture option → execute
        const pendingArr = [...pendingTableIds];
        const exactMatch = $captureOptions.find(opt =>
            opt.length === pendingArr.length &&
            pendingArr.every(id => opt.includes(id))
        );
        if (exactMatch) {
            executePlay($selectedCard.id, exactMatch);
        }
    }

    function executePlay(cardId, captIds) {
        sendPlay(cardId, captIds);
        selectedCard  .set(null);
        captureOptions.set([]);
        capturesLoaded.set(false);
        pendingTableIds = new Set();
    }

    function cancelSelection() {
        selectedCard  .set(null);
        captureOptions.set([]);
        capturesLoaded.set(false);
        pendingTableIds = new Set();
    }

    // ── Derived display values ────────────────────────────────────────────────

    $: myScore      = $scores[$playerId]   ?? 0;
    $: oppScore     = $scores[$opponentId] ?? 0;
    $: myInfo       = $gameState?.players?.[$playerId]   ?? {};
    $: oppInfo      = $gameState?.players?.[$opponentId] ?? {};
    $: phase        = $gameState?.phase ?? 'playing';
    $: deckLeft     = $gameState?.deck_remaining ?? 0;
    $: isMyTurnNow  = $isMyTurn;

    const SUIT_ICON = { bastoni: '🪵', coppe: '🏆', oro: '🪙', spade: '⚔️' };
</script>

{#if !$gameState}
    <!-- Board waiting for first state after deal animation -->
    <div class="board-empty"></div>
{:else}
<div class="board">

    <!-- ── Opponent ─────────────────────────────────────────────────────────── -->
    <div class="zone opponent-zone">
        <div class="player-bar">
            <span class="player-name">Opponent</span>
            <div class="stats">
                <span>📦 {oppInfo.captured_count ?? 0}</span>
                <span>🧹 {oppInfo.scopas ?? 0}</span>
                <span class="pts">{oppScore} pts</span>
            </div>
            {#if $gameState && !isMyTurnNow}
                <span class="badge thinking">thinking…</span>
            {/if}
        </div>
        <div class="hand-row">
            <CardBack count={oppInfo.hand_count ?? 0} />
        </div>
    </div>

    <!-- ── Table ─────────────────────────────────────────────────────────────── -->
    <div class="zone table-zone">
        <div class="zone-header">
            <span class="zone-label">Table</span>
            <span class="deck-pill">🂠 {deckLeft} in deck</span>
        </div>
        <div class="card-row table-cards">
            {#each $tableCards as card (card.id)}
                <Card
                    {card}
                    capturable={!!$selectedCard && isMyTurnNow && capturableIds.has(card.id) && !pendingTableIds.has(card.id)}
                    pending={!!$selectedCard && isMyTurnNow && pendingTableIds.has(card.id)}
                    animateIn={true}
                    on:click={() => handleTableCard(card)}
                />
            {/each}
            {#if $tableCards.length === 0}
                <span class="empty">Table is empty</span>
            {/if}
        </div>
    </div>

    <!-- ── Scopa toast ─────────────────────────────────────────────────────── -->
    {#if $lastScopaBy}
        <div class="scopa-toast" class:scopa-mine={$lastScopaBy.is_mine}>
            🧹 {$lastScopaBy.is_mine ? '¡Scopa!' : 'Scopa del oponente!'}
        </div>
    {/if}

    <!-- ── Error banner ──────────────────────────────────────────────────────── -->
    {#if $errorMessage}
        <div class="error-banner" role="alert">
            ⚠️ {$errorMessage}
        </div>
    {/if}

    <!-- ── Round-over overlay ────────────────────────────────────────────────── -->
    {#if $roundResult}
        <div class="overlay" role="dialog" aria-modal="true">
            <div class="result-card">
                <div class="result-icon">🎉</div>
                <h2>Round {$roundResult.round_number} complete</h2>

                <div class="result-rows">
                    <div class="result-row">
                        <span>You</span>
                        <span class="gain">+{$roundResult.round_scores?.[$playerId] ?? 0} pts</span>
                    </div>
                    <div class="result-row">
                        <span>Opponent</span>
                        <span class="gain">+{$roundResult.round_scores?.[$opponentId] ?? 0} pts</span>
                    </div>
                </div>

                <p class="cumul">
                    Total — You: <strong>{$roundResult.cumulative?.[$playerId] ?? 0}</strong>
                    &nbsp;|&nbsp;
                    Opp: <strong>{$roundResult.cumulative?.[$opponentId] ?? 0}</strong>
                </p>
                <p class="next-hint">Next round starting…</p>
            </div>
        </div>
    {/if}

    <!-- ── Your hand ─────────────────────────────────────────────────────────── -->
    <div class="zone player-zone">
        <div class="player-bar">
            <span class="player-name">You</span>
            <div class="stats">
                <span>📦 {myInfo.captured_count ?? 0}</span>
                <span>🧹 {myInfo.scopas ?? 0}</span>
                <span class="pts">{myScore} pts</span>
            </div>
            {#if isMyTurnNow}
                <span class="badge your-turn">Your turn ✨</span>
            {/if}
        </div>

        <div class="card-row hand-row">
            {#each $myHand as card (card.id)}
                <Card
                    {card}
                    selectable={isMyTurnNow}
                    selected={$selectedCard?.id === card.id}
                    animateIn={true}
                    on:click={() => handleHandCard(card)}
                />
            {/each}
        </div>

        <!-- ── Capture hint strip ───────────────────────────────────────────── -->
        {#if $selectedCard && isMyTurnNow}
            <div class="capture-hint">
                {#if $captureOptions.length > 0 && pendingTableIds.size > 0}
                    <span class="hint-text">Tap more cards to complete the combination, or tap a selected card to undo</span>
                {:else if $captureOptions.length > 0}
                    <span class="hint-text">Tap a glowing card on the table to capture ✨</span>
                {:else if $capturesLoaded}
                    <span class="hint-discard">No captures — tap your card again to discard</span>
                {:else}
                    <span class="hint-text">{SUIT_ICON[$selectedCard.suit] ?? ''} {$selectedCard.value} selected — tap again to discard if no captures</span>
                {/if}
                <button class="btn-cancel" on:click={cancelSelection} aria-label="Cancel">✕</button>
            </div>
        {/if}
    </div>

</div>
{/if}

<style>
    /* ── Board layout ──────────────────────────────────────────────────────── */
    .board-empty {
        min-height:  100dvh;
        background:  linear-gradient(180deg, #1a4731 0%, #143d27 100%);
    }

    .board {
        display:        flex;
        flex-direction: column;
        gap:            10px;
        min-height:     100dvh;
        padding:        10px;
        background:     linear-gradient(180deg, #1a4731 0%, #143d27 100%);
        position:       relative;
        overflow:       hidden;
    }

    /* ── Zone cards ────────────────────────────────────────────────────────── */
    .zone {
        background:    rgba(0,0,0,0.18);
        border:        1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding:       12px;
    }

    .table-zone {
        flex:       1;
        min-height: 140px;
    }

    /* ── Zone header ───────────────────────────────────────────────────────── */
    .zone-header {
        display:         flex;
        justify-content: space-between;
        align-items:     center;
        margin-bottom:   8px;
    }

    .zone-label {
        font-size:     11px;
        font-weight:   700;
        color:         rgba(255,255,255,0.5);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .deck-pill {
        font-size:     11px;
        color:         rgba(255,255,255,0.35);
    }

    /* ── Card rows ──────────────────────────────────────────────────────────── */
    .card-row {
        display:    flex;
        flex-wrap:  wrap;
        gap:        8px;
        align-items: flex-end;
    }

    .table-cards { min-height: 96px; }

    .empty {
        color:       rgba(255,255,255,0.25);
        font-style:  italic;
        font-size:   13px;
        align-self:  center;
    }

    /* ── Player bars ────────────────────────────────────────────────────────── */
    .player-bar {
        display:     flex;
        align-items: center;
        gap:         10px;
        flex-wrap:   wrap;
        margin-bottom: 8px;
    }

    .player-name {
        font-weight: 700;
        color:       white;
        font-size:   14px;
    }

    .stats {
        display:   flex;
        gap:       8px;
        color:     rgba(255,255,255,0.6);
        font-size: 12px;
        flex-wrap: wrap;
    }

    .pts  { font-weight: 700; color: #fbbf24; }

    .badge {
        font-size:     11px;
        padding:       3px 10px;
        border-radius: 999px;
        font-weight:   600;
    }

    .thinking {
        background: rgba(255,255,255,0.12);
        color:      rgba(255,255,255,0.55);
        font-style: italic;
        font-weight: 400;
    }

    .your-turn {
        background:  #15803d;
        color:       white;
        animation:   pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0.75; }
    }

    /* ── Capture hint strip ─────────────────────────────────────────────────── */
    .capture-hint {
        display:      flex;
        align-items:  center;
        gap:          8px;
        margin-top:   10px;
        padding:      8px 12px;
        border-radius: 10px;
        background:   rgba(0,0,0,0.2);
        border-top:   1px solid rgba(255,255,255,0.08);
    }

    .hint-text {
        flex:        1;
        color:       rgba(255,255,255,0.55);
        font-size:   12px;
        font-style:  italic;
    }

    .hint-discard {
        flex:        1;
        color:       #fbbf24;
        font-size:   12px;
        font-weight: 600;
    }

    .btn-cancel {
        background: none;
        border:     none;
        color:      rgba(255,255,255,0.4);
        font-size:  16px;
        cursor:     pointer;
        padding:    2px 6px;
        border-radius: 6px;
        line-height: 1;
        transition: color 0.15s;
        flex-shrink: 0;
    }
    .btn-cancel:hover { color: rgba(255,255,255,0.85); }

    /* ── Scopa toast ────────────────────────────────────────────────────────── */
    .scopa-toast {
        position:        fixed;
        top:             50%;
        left:            50%;
        transform:       translate(-50%, -50%);
        background:      rgba(15, 52, 30, 0.92);
        border:          2px solid #22c55e;
        color:           #bbf7d0;
        font-size:       clamp(28px, 7vw, 48px);
        font-weight:     900;
        letter-spacing:  0.05em;
        padding:         18px 36px;
        border-radius:   20px;
        box-shadow:      0 0 40px rgba(34, 197, 94, 0.45), 0 8px 32px rgba(0,0,0,0.6);
        z-index:         200;
        pointer-events:  none;
        animation:       scopa-pop 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) both,
                         scopa-fade 0.5s ease-in 2s forwards;
        text-shadow:     0 2px 12px rgba(34, 197, 94, 0.6);
        white-space:     nowrap;
    }

    .scopa-mine {
        background: rgba(14, 42, 10, 0.94);
        border-color: #4ade80;
        color:        #dcfce7;
        box-shadow:   0 0 60px rgba(74, 222, 128, 0.6), 0 8px 32px rgba(0,0,0,0.6);
    }

    @keyframes scopa-pop {
        from { transform: translate(-50%, -50%) scale(0.4); opacity: 0; }
        to   { transform: translate(-50%, -50%) scale(1);   opacity: 1; }
    }

    @keyframes scopa-fade {
        from { opacity: 1; }
        to   { opacity: 0; }
    }

    /* ── Error banner ───────────────────────────────────────────────────────── */
    .error-banner {
        background:    #dc2626;
        color:         white;
        text-align:    center;
        padding:       10px 16px;
        border-radius: 10px;
        font-weight:   600;
        font-size:     14px;
        animation:     slide-down 0.2s ease-out;
    }

    @keyframes slide-down {
        from { transform: translateY(-8px); opacity: 0; }
        to   { transform: translateY(0);    opacity: 1; }
    }

    /* ── Round-over overlay ─────────────────────────────────────────────────── */
    .overlay {
        position:        fixed;
        inset:           0;
        background:      rgba(0,0,0,0.72);
        display:         flex;
        align-items:     center;
        justify-content: center;
        z-index:         50;
        animation:       fade-in 0.25s ease-out;
    }

    @keyframes fade-in {
        from { opacity: 0; }
        to   { opacity: 1; }
    }

    .result-card {
        background:    #fdf6e3;
        border-radius: 20px;
        padding:       36px 28px;
        text-align:    center;
        max-width:     340px;
        width:         92%;
        box-shadow:    0 24px 60px rgba(0,0,0,0.55);
        animation:     pop-in 0.3s cubic-bezier(0.34,1.56,0.64,1) both;
    }

    @keyframes pop-in {
        from { transform: scale(0.85); opacity: 0; }
        to   { transform: scale(1);    opacity: 1; }
    }

    .result-icon { font-size: 52px; margin-bottom: 8px; }

    .result-card h2 {
        font-size:   22px;
        font-weight: 800;
        color:       #1a4731;
        margin:      0 0 18px;
    }

    .result-rows {
        display:        flex;
        flex-direction: column;
        gap:            8px;
        margin-bottom:  16px;
    }

    .result-row {
        display:         flex;
        justify-content: space-between;
        padding:         10px 14px;
        background:      rgba(0,0,0,0.05);
        border-radius:   10px;
        font-size:       15px;
    }

    .gain { font-weight: 700; color: #16a34a; }

    .cumul {
        color:      #555;
        font-size:  13px;
        margin:     0 0 10px;
    }

    .next-hint {
        color:       #2d6a4f;
        font-weight: 600;
        font-size:   14px;
        margin:      0;
        animation:   pulse 1.5s ease-in-out infinite;
    }
</style>
