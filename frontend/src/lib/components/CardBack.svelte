<!--
    CardBack.svelte
    ===============
    Renders a face-down card stack for the opponent's hand.
    Stacks up to 5 cards visually with an offset effect.

    Props
    -----
    count  number  — total number of cards in the opponent's hand
-->
<script>
    export let count = 0;
    $: stackCount = Math.min(count, 4);
</script>

<div class="stack" aria-label="{count} card{count !== 1 ? 's' : ''}">
    {#each Array(stackCount) as _, i}
        <div
            class="back"
            style="
                transform:  translate({i * 4}px, {i * -3}px);
                z-index:    {i};
                opacity:    {0.65 + i * 0.12};
            "
        ></div>
    {/each}

    {#if count > 0}
        <span class="badge">{count}</span>
    {/if}
</div>

<style>
    .stack {
        position:    relative;
        display:     inline-flex;
        align-items: flex-end;
        min-width:   64px;
        min-height:  96px;
    }

    .back {
        position:         absolute;
        left:             0;
        bottom:           0;
        width:            64px;
        height:           96px;
        border-radius:    7px;
        background:       url('/assets/reverso.png') center / cover no-repeat;
        background-color: #1a1a2e;  /* fallback */
        border:           2px solid rgba(255,255,255,0.15);
        box-shadow:       0 2px 8px rgba(0,0,0,0.45);
    }

    .badge {
        position:        absolute;
        right:           -10px;
        bottom:          -8px;
        background:      #1e3d6f;
        color:           white;
        font-size:       11px;
        font-weight:     700;
        width:           22px;
        height:          22px;
        border-radius:   50%;
        display:         flex;
        align-items:     center;
        justify-content: center;
        border:          2px solid rgba(255,255,255,0.8);
        z-index:         10;
    }

    @media (min-width: 480px) {
        .stack { min-width: 80px; min-height: 120px; }
        .back  { width: 80px; height: 120px; }
    }

    @media (min-width: 768px) {
        .stack { min-width: 92px; min-height: 138px; }
        .back  { width: 92px; height: 138px; }
    }
</style>
