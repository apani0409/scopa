<!--
    DealAnimation.svelte
    ====================
    Full-screen overlay that animates card dealing at the start of a round.

    Cards fly from a central deck to three destinations:
      • 4 cards → table   (center, fanned)
      • 3 cards → opponent (top)
      • 3 cards → player   (bottom)

    Emits: dispatch('done') when the animation has finished.
-->
<script>
    import { createEventDispatcher, onMount } from 'svelte';

    export let round = 1;     // shown as "Round N"
    export let type  = 'full'; // 'full' = 4-table + 3+3 hands | 'hands' = 3+3 hands only

    const dispatch = createEventDispatcher();

    // ── Deal sequences ─────────────────────────────────────────────────────────
    const SEQUENCE_FULL = [
        { dest: 'table',    idx: 0 },
        { dest: 'table',    idx: 1 },
        { dest: 'table',    idx: 2 },
        { dest: 'table',    idx: 3 },
        { dest: 'player',   idx: 0 },
        { dest: 'opponent', idx: 0 },
        { dest: 'player',   idx: 1 },
        { dest: 'opponent', idx: 1 },
        { dest: 'player',   idx: 2 },
        { dest: 'opponent', idx: 2 },
    ];

    const SEQUENCE_HANDS = [
        { dest: 'player',   idx: 0 },
        { dest: 'opponent', idx: 0 },
        { dest: 'player',   idx: 1 },
        { dest: 'opponent', idx: 1 },
        { dest: 'player',   idx: 2 },
        { dest: 'opponent', idx: 2 },
    ];

    const SEQUENCE = type === 'hands' ? SEQUENCE_HANDS : SEQUENCE_FULL;

    const DEAL_INTERVAL  = 130;   // ms between each card
    const CARD_DURATION  = 500;   // ms for one card's flight
    const FINISH_DELAY   = 600;   // ms to pause before emitting 'done'

    // ── Final positions relative to the deck (percentage of viewport) ──────────
    // These are CSS --tx / --ty custom properties set per card.
    function getTranslate(dest, idx) {
        switch (dest) {
            case 'table':
                // Fan 4 cards horizontally in the centre
                return { tx: `${(idx - 1.5) * 80}px`, ty: `0px` };
            case 'opponent':
                // Fan 3 cards near the top
                return { tx: `${(idx - 1) * 72}px`,   ty: `-42vh` };
            case 'player':
                // Fan 3 cards near the bottom
                return { tx: `${(idx - 1) * 72}px`,   ty: `42vh`  };
        }
    }

    // ── Reactive card state ────────────────────────────────────────────────────
    let cards = SEQUENCE.map((item, i) => ({
        ...item,
        ...getTranslate(item.dest, item.idx),
        flying:  false,
        landed:  false,
        delay:   i * DEAL_INTERVAL,
    }));

    let deckGlow = false;

    onMount(() => {
        // Brief pause, then start dealing
        setTimeout(() => {
            deckGlow = true;
            cards.forEach((card, i) => {
                setTimeout(() => {
                    cards[i].flying = true;
                    cards = cards;  // trigger reactivity

                    setTimeout(() => {
                        cards[i].landed = true;
                        cards = cards;
                    }, CARD_DURATION);
                }, card.delay);
            });

            const totalMs = SEQUENCE.length * DEAL_INTERVAL + CARD_DURATION + FINISH_DELAY;
            setTimeout(() => dispatch('done'), totalMs);
        }, 350);
    });
</script>

<!-- ── Overlay ──────────────────────────────────────────────────────────────── -->
<div class="overlay">

    <!-- Round label -->
    <div class="round-label">Round {round}</div>

    <!-- Opponent zone hint -->
    <div class="zone-hint top">Opponent</div>

    <!-- Table zone hint (only shown for full deal) -->
    {#if type === 'full'}
        <div class="zone-hint mid">Table</div>
    {/if}

    <!-- Player zone hint -->
    <div class="zone-hint bot">You</div>

    <!-- Deck ─────────────────────────────────────────────────────────────────── -->
    <div class="deck" class:glow={deckGlow}>
        {#each [4,3,2,1,0] as z}
            <div class="deck-card" style="transform: translate({z*1.5}px, {-z*1.5}px)"></div>
        {/each}
    </div>

    <!-- Flying cards ─────────────────────────────────────────────────────────── -->
    {#each cards as card}
        <div
            class="flying-card"
            class:fly={card.flying}
            class:landed={card.landed}
            style="--tx:{card.tx}; --ty:{card.ty}; --dur:{CARD_DURATION}ms;"
        ></div>
    {/each}
</div>

<style>
    /* ── Overlay ──────────────────────────────────────────────────────────────── */
    .overlay {
        position: fixed;
        inset:    0;
        background: linear-gradient(160deg, #1a4731 0%, #0d2818 100%);
        display:  flex;
        align-items:     center;
        justify-content: center;
        z-index: 100;
        overflow: hidden;
    }

    /* ── Zone hints ───────────────────────────────────────────────────────────── */
    .round-label {
        position:    absolute;
        top:         20px;
        left:        50%;
        transform:   translateX(-50%);
        color:       rgba(255,255,255,0.9);
        font-size:   22px;
        font-weight: 800;
        letter-spacing: 0.05em;
        text-shadow: 0 2px 12px rgba(0,0,0,0.5);
    }

    .zone-hint {
        position:   absolute;
        left:       50%;
        transform:  translateX(-50%);
        color:      rgba(255,255,255,0.22);
        font-size:  12px;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .zone-hint.top { top:    12%; }
    .zone-hint.mid { top:    50%; margin-top: -6px; }
    .zone-hint.bot { bottom: 12%; }

    /* ── Deck ─────────────────────────────────────────────────────────────────── */
    .deck {
        position: relative;
        width:    72px;
        height:   108px;
        transition: filter 0.3s;
    }

    .deck.glow {
        filter: drop-shadow(0 0 18px rgba(251, 191, 36, 0.7));
    }

    .deck-card {
        position:      absolute;
        inset:         0;
        border-radius: 7px;
        background:    url('/assets/reverso.png') center / cover no-repeat;
        box-shadow:    0 2px 10px rgba(0,0,0,0.5);
        /* CSS card back fallback when image not found */
        background-color: #1a1a2e;
    }

    /* ── Flying cards ─────────────────────────────────────────────────────────── */
    .flying-card {
        position:      absolute;
        /* Start at deck centre */
        top:     50%;
        left:    50%;
        margin-top:  -54px;   /* half of 108px height */
        margin-left: -36px;   /* half of 72px width  */
        width:         72px;
        height:        108px;
        border-radius: 7px;
        background:    url('/assets/reverso.png') center / cover no-repeat;
        background-color: #1a1a2e;
        box-shadow:    0 4px 16px rgba(0,0,0,0.5);

        /* Default: invisible at deck position */
        opacity:   0;
        transform: translate(0, 0) rotate(0deg) scale(0.95);
        will-change: transform, opacity;
    }

    /* Phase 1: fly from deck to destination */
    .flying-card.fly {
        opacity:    1;
        transform:  translate(var(--tx), var(--ty)) rotate(0deg) scale(1);
        transition:
            transform var(--dur) cubic-bezier(0.22, 0.68, 0.35, 1.1),
            opacity   80ms ease-out;
    }

    /* Phase 2: landed — slightly dim + tiny rotation for a natural pile */
    .flying-card.landed {
        opacity: 0.92;
    }
</style>
