<script>
    import { onMount, onDestroy }  from 'svelte';
    import { page }                from '$app/stores';
    import { goto }                from '$app/navigation';
    import GameBoard               from '$lib/components/GameBoard.svelte';
    import DealAnimation           from '$lib/components/DealAnimation.svelte';
    import {
        sessionId, playerId, joinCode,
        wsStatus, gameState, isWaiting,
        isDealing, roundNumber, dealType,
    } from '$lib/stores/game.js';
    import { connect, disconnect } from '$lib/ws.js';

    const sid = $page.params.session_id;

    let copied = false;

    async function copyCode() {
        if ($joinCode) {
            await navigator.clipboard.writeText($joinCode);
            copied = true;
            setTimeout(() => (copied = false), 2000);
        }
    }

    onMount(() => {
        // Restore identity from sessionStorage on page refresh
        let pid = $playerId;
        if (!pid) {
            pid             = sessionStorage.getItem('scopa_player_id');
            const storedSid = sessionStorage.getItem('scopa_session_id');
            const storedCode= sessionStorage.getItem('scopa_join_code');
            if (!pid || storedSid !== sid) {
                goto('/');
                return;
            }
            sessionId.set(sid);
            playerId .set(pid);
            if (storedCode) joinCode.set(storedCode);
        }
        connect(sid, pid);
    });

    onDestroy(() => {
        disconnect();
    });

    $: isConnecting          = $wsStatus === 'connecting';
    $: isWaitingForOpponent  = $wsStatus === 'waiting' || $isWaiting;
    $: isPlaying             = $wsStatus === 'connected' && $gameState !== null;
    $: isDisconnected        = $wsStatus === 'disconnected';
</script>

<svelte:head>
    <title>Scopa · Game</title>
</svelte:head>

<!-- ── Connecting spinner ────────────────────────────────────────────────── -->
{#if isConnecting}
    <div class="overlay">
        <div class="spinner"></div>
        <p>Connecting…</p>
    </div>

<!-- ── Lobby: waiting for opponent ──────────────────────────────────────── -->
{:else if isWaitingForOpponent}
    <div class="overlay">
        <div class="lobby">
            <div class="lobby-icon">🃏</div>
            <h2>Waiting for opponent</h2>

            {#if $joinCode}
                <p class="hint">Share this code with your friend:</p>
                <div class="join-code">{$joinCode}</div>
                <button class="btn-copy" on:click={copyCode}>
                    {copied ? '✅ Copied!' : '📋 Copy Code'}
                </button>
            {/if}

            <p class="sub-hint">The game starts automatically when they connect.</p>
            <div class="spinner-sm"></div>
        </div>
    </div>

<!-- ── Disconnected ──────────────────────────────────────────────────────── -->
{:else if isDisconnected && !$gameState}
    <div class="overlay">
        <div class="lobby">
            <div class="lobby-icon">⚡</div>
            <h2>Disconnected</h2>
            <p class="hint">The connection was lost.</p>
            <button class="btn-home" on:click={() => goto('/')}>← Home</button>
        </div>
    </div>

<!-- ── Active game ───────────────────────────────────────────────────────── -->
{:else}
    {#if $isDealing}
        <DealAnimation round={$roundNumber} type={$dealType} on:done={() => isDealing.set(false)} />
    {/if}
    <!-- Board is always mounted once game_started; hidden behind deal anim -->
    {#if !$isDealing || $gameState}
        <GameBoard />
    {/if}
{/if}

<style>
    .overlay {
        min-height: 100dvh;
        display:         flex;
        align-items:     center;
        justify-content: center;
        background: linear-gradient(160deg, #1a4731 0%, #0d2818 100%);
        color: white;
    }

    .lobby {
        display:        flex;
        flex-direction: column;
        align-items:    center;
        gap:       18px;
        padding:   36px 28px;
        background:    rgba(255,255,255,0.06);
        border:        1px solid rgba(255,255,255,0.12);
        border-radius: 20px;
        max-width: 380px;
        width: 90%;
        text-align: center;
    }

    .lobby-icon { font-size: 64px; filter: drop-shadow(0 2px 8px rgba(0,0,0,0.4)); }

    h2 { font-size: 22px; font-weight: 700; margin: 0; }

    .hint     { color: rgba(255,255,255,0.65); font-size: 14px; margin: 0; }
    .sub-hint { color: rgba(255,255,255,0.35); font-size: 12px; margin: 0; }

    .join-code {
        background:    rgba(0,0,0,0.35);
        border:        1px solid rgba(255,255,255,0.2);
        border-radius: 14px;
        padding:       18px 36px;
        font-size:     40px;
        font-weight:   900;
        letter-spacing: 0.25em;
        color:         #fbbf24;
        user-select: all;
    }

    .btn-copy {
        background:    rgba(255,255,255,0.1);
        border:        1px solid rgba(255,255,255,0.2);
        color:         white;
        padding:       10px 22px;
        border-radius: 10px;
        cursor:        pointer;
        font-size:     14px;
        font-weight:   600;
        transition:    background 0.15s;
    }
    .btn-copy:hover { background: rgba(255,255,255,0.18); }

    .btn-home {
        background:    rgba(255,255,255,0.1);
        border:        1px solid rgba(255,255,255,0.2);
        color:         white;
        padding:       12px 28px;
        border-radius: 10px;
        cursor:        pointer;
        font-size:     15px;
        font-weight:   600;
        transition:    background 0.15s;
    }
    .btn-home:hover { background: rgba(255,255,255,0.18); }

    .spinner {
        width:  48px;
        height: 48px;
        border: 4px solid rgba(255,255,255,0.2);
        border-top-color: white;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }

    .spinner-sm {
        width:  28px;
        height: 28px;
        border: 3px solid rgba(255,255,255,0.2);
        border-top-color: rgba(255,255,255,0.6);
        border-radius: 50%;
        animation: spin 0.9s linear infinite;
    }

    @keyframes spin { to { transform: rotate(360deg); } }
</style>
