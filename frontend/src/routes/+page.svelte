<script>
    import { goto } from '$app/navigation';
    import { sessionId, playerId, joinCode } from '$lib/stores/game.js';

    let mode         = 'menu';   // 'menu' | 'create' | 'join'
    let joinInput    = '';
    let loading      = false;
    let errorMsg     = '';

    async function createGame() {
        loading  = true;
        errorMsg = '';
        try {
            const res = await fetch('/api/session', { method: 'POST' });
            if (!res.ok) throw new Error('Could not create session — is the server running?');
            const data = await res.json();

            sessionId.set(data.session_id);
            playerId .set(data.player_id);
            joinCode .set(data.join_code);

            sessionStorage.setItem('scopa_session_id', data.session_id);
            sessionStorage.setItem('scopa_player_id',  data.player_id);
            sessionStorage.setItem('scopa_join_code',  data.join_code);

            goto(`/game/${data.session_id}`);
        } catch (e) {
            errorMsg = e.message;
        } finally {
            loading = false;
        }
    }

    async function joinGame() {
        if (!joinInput.trim()) return;
        loading  = true;
        errorMsg = '';
        try {
            const res = await fetch('/api/session/join', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ join_code: joinInput.trim().toUpperCase() }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Could not join session.');

            sessionId.set(data.session_id);
            playerId .set(data.player_id);
            joinCode .set(null);

            sessionStorage.setItem('scopa_session_id', data.session_id);
            sessionStorage.setItem('scopa_player_id',  data.player_id);
            sessionStorage.removeItem('scopa_join_code');

            goto(`/game/${data.session_id}`);
        } catch (e) {
            errorMsg = e.message;
        } finally {
            loading = false;
        }
    }
</script>

<svelte:head>
    <title>Scopa</title>
</svelte:head>

<main class="home">
    <div class="hero">
        <div class="logo">🃏</div>
        <h1>Scopa</h1>
        <p class="subtitle">The classic Italian card game — now multiplayer</p>
    </div>

    {#if mode === 'menu'}
        <div class="menu">
            <button class="btn-primary" on:click={() => (mode = 'create')}>
                Create Game
            </button>
            <button class="btn-secondary" on:click={() => (mode = 'join')}>
                Join Game
            </button>
        </div>

    {:else if mode === 'create'}
        <div class="panel">
            <h2>Create Game</h2>
            <p>A 6-letter code will be generated.<br />Share it with a friend to start playing.</p>
            {#if errorMsg}<div class="error">{errorMsg}</div>{/if}
            <button class="btn-primary" on:click={createGame} disabled={loading}>
                {loading ? 'Creating…' : '✅  Create Game'}
            </button>
            <button class="btn-back" on:click={() => { mode = 'menu'; errorMsg = ''; }}>
                ← Back
            </button>
        </div>

    {:else if mode === 'join'}
        <div class="panel">
            <h2>Join Game</h2>
            <p>Enter the code your friend shared with you.</p>
            <!-- svelte-ignore a11y-autofocus -->
            <input
                class="code-input"
                bind:value={joinInput}
                placeholder="XXXXXX"
                maxlength="6"
                autofocus
                on:input={() => (joinInput = joinInput.toUpperCase())}
                on:keydown={(e) => e.key === 'Enter' && joinGame()}
            />
            {#if errorMsg}<div class="error">{errorMsg}</div>{/if}
            <button
                class="btn-primary"
                on:click={joinGame}
                disabled={loading || !joinInput.trim()}
            >
                {loading ? 'Joining…' : '🎮  Join Game'}
            </button>
            <button class="btn-back" on:click={() => { mode = 'menu'; errorMsg = ''; joinInput = ''; }}>
                ← Back
            </button>
        </div>
    {/if}
</main>

<style>
    .home {
        min-height: 100dvh;
        display:        flex;
        flex-direction: column;
        align-items:    center;
        justify-content: center;
        gap:     40px;
        padding: 24px;
        background: linear-gradient(160deg, #1a4731 0%, #0d2818 100%);
    }

    .hero { text-align: center; }

    .logo {
        font-size: 88px;
        line-height: 1;
        filter: drop-shadow(0 4px 12px rgba(0,0,0,0.5));
    }

    h1 {
        font-size:      52px;
        font-weight:    900;
        color:          white;
        letter-spacing: -0.03em;
        margin: 8px 0 4px;
    }

    .subtitle {
        color:     rgba(255,255,255,0.55);
        font-size: 15px;
    }

    .menu, .panel {
        display:        flex;
        flex-direction: column;
        gap:       12px;
        width:     100%;
        max-width: 320px;
    }

    .panel {
        background:    rgba(255,255,255,0.06);
        border:        1px solid rgba(255,255,255,0.12);
        border-radius: 18px;
        padding:       28px 24px;
    }

    .panel h2 {
        color:       white;
        font-size:   20px;
        font-weight: 700;
        margin:      0 0 4px;
    }

    .panel p {
        color:       rgba(255,255,255,0.55);
        font-size:   14px;
        line-height: 1.5;
        margin:      0 0 16px;
    }

    .btn-primary {
        background:    #16a34a;
        color:         white;
        border:        none;
        padding:       15px;
        border-radius: 12px;
        font-weight:   700;
        font-size:     16px;
        cursor:        pointer;
        transition:    background 0.15s, transform 0.1s;
    }
    .btn-primary:hover:not(:disabled) { background: #15803d; transform: translateY(-1px); }
    .btn-primary:disabled             { opacity: 0.5; cursor: not-allowed; }

    .btn-secondary {
        background:    rgba(255,255,255,0.08);
        color:         white;
        border:        1px solid rgba(255,255,255,0.18);
        padding:       15px;
        border-radius: 12px;
        font-weight:   600;
        font-size:     16px;
        cursor:        pointer;
        transition:    background 0.15s;
    }
    .btn-secondary:hover { background: rgba(255,255,255,0.14); }

    .btn-back {
        background:  none;
        border:      none;
        color:       rgba(255,255,255,0.45);
        cursor:      pointer;
        font-size:   14px;
        padding:     8px;
        text-align:  center;
        transition:  color 0.15s;
    }
    .btn-back:hover { color: white; }

    .code-input {
        background:    rgba(255,255,255,0.1);
        border:        1px solid rgba(255,255,255,0.3);
        border-radius: 12px;
        padding:       14px;
        color:         #fbbf24;
        font-size:     28px;
        font-weight:   800;
        letter-spacing: 0.3em;
        text-align:    center;
        width:         100%;
        outline:       none;
        transition:    border-color 0.15s;
    }
    .code-input::placeholder { color: rgba(255,255,255,0.25); letter-spacing: 0.2em; }
    .code-input:focus        { border-color: #16a34a; }

    .error {
        background:    #dc2626;
        color:         white;
        padding:       10px 14px;
        border-radius: 10px;
        font-size:     14px;
        font-weight:   500;
    }
</style>
