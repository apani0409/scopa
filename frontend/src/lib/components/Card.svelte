<!--
    Card.svelte
    ===========
    Renders a single face-up Scopa card as a responsive, interactive button.

    Props
    -----
    card        {id, suit, value, image_url}
    selectable  bool  — player can click this card (it's in their hand + their turn)
    selected    bool  — currently selected (lifted + gold ring)
    capturable  bool  — a valid capture target (green ring on hover)
    animateIn   bool  — play deal animation on mount
-->
<script>
    import { createEventDispatcher } from 'svelte';
    import { fly }                   from 'svelte/transition';

    /** @type {{id:string, suit:string, value:number, image_url:string}} */
    export let card;
    export let selectable  = false;
    export let selected    = false;
    export let capturable  = false;
    export let pending     = false;  // selected as part of a multi-card combination
    export let animateIn   = false;

    const dispatch = createEventDispatcher();

    function handleClick() {
        if (selectable || capturable || pending) dispatch('click', card);
    }

    $: alt = `${card.value} di ${card.suit}`;
</script>

{#if animateIn}
    <div in:fly={{ y: 24, duration: 260, opacity: 0 }}>
        <button
            class="card"
            class:selectable
            class:selected
            class:capturable
            class:pending
            on:click={handleClick}
            aria-label={alt}
            disabled={!selectable && !capturable && !pending}
        >
            <img src={card.image_url} {alt} draggable="false" />
        </button>
    </div>
{:else}
    <button
        class="card"
        class:selectable
        class:selected
        class:capturable
        class:pending
        on:click={handleClick}
        aria-label={alt}
        disabled={!selectable && !capturable && !pending}
    >
        <img src={card.image_url} {alt} draggable="false" />
    </button>
{/if}

<style>
    .card {
        display:       block;
        padding:       0;
        background:    none;
        border:        none;
        border-radius: 7px;
        cursor:        default;
        transition:    transform 0.15s ease, box-shadow 0.15s ease;
        box-shadow:    0 2px 8px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2);
        outline:       none;
    }

    img {
        display:       block;
        width:         64px;
        height:        auto;
        border-radius: 7px;
        user-select:   none;
    }

    /* ── Selectable (hand card, player's turn) ──────────────────────────────── */
    .selectable { cursor: pointer; }

    .selectable:hover:not(.selected) {
        transform:  translateY(-10px) scale(1.06);
        box-shadow: 0 10px 24px rgba(0,0,0,0.4);
    }

    /* ── Selected (picked up, awaiting capture choice) ──────────────────────── */
    .selected {
        transform:  translateY(-14px) scale(1.08);
        box-shadow: 0 0 0 3px #f59e0b, 0 10px 28px rgba(0,0,0,0.45);
    }

    /* ── Capturable (valid table target) ────────────────────────────────────────── */
    .capturable { cursor: pointer; }

    .capturable:hover:not(.pending) {
        transform:  translateY(-5px) scale(1.04);
        box-shadow: 0 0 0 3px #22c55e, 0 6px 16px rgba(0,0,0,0.3);
    }

    /* ── Pending (chosen for a multi-card sum combination) ───────────────────── */
    .pending {
        cursor:     pointer;
        transform:  translateY(-7px) scale(1.06);
        box-shadow: 0 0 0 3px #38bdf8, 0 8px 20px rgba(0,0,0,0.4);
    }
    .pending:hover {
        box-shadow: 0 0 0 3px #7dd3fc, 0 8px 24px rgba(0,0,0,0.45);
    }

    /* ── Responsive: wider screens ──────────────────────────────────────────── */
    @media (min-width: 480px) {
        img { width: 80px; }
    }

    @media (min-width: 768px) {
        img { width: 92px; }
    }
</style>
