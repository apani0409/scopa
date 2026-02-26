import { a as ssr_context, g as getContext, f as fallback, b as attr_class, c as attr, d as bind_props, i as ensure_array_like, j as attr_style, e as escape_html, k as stringify, l as store_get, u as unsubscribe_stores, h as head } from "../../../../chunks/index.js";
import "clsx";
import "@sveltejs/kit/internal";
import "../../../../chunks/exports.js";
import "../../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../../chunks/root.js";
import "../../../../chunks/state.svelte.js";
import { c as captureOptions, s as selectedCard, a as scores, p as playerId, o as opponentId, g as gameState, i as isMyTurn, t as tableCards, l as lastScopaBy, e as errorMessage, r as roundResult, m as myHand, b as capturesLoaded, w as wsStatus, d as isWaiting, j as joinCode, f as isDealing, h as dealType, k as roundNumber } from "../../../../chunks/game.js";
function onDestroy(fn) {
  /** @type {SSRContext} */
  ssr_context.r.on_destroy(fn);
}
const getStores = () => {
  const stores$1 = getContext("__svelte__");
  return {
    /** @type {typeof page} */
    page: {
      subscribe: stores$1.page.subscribe
    },
    /** @type {typeof navigating} */
    navigating: {
      subscribe: stores$1.navigating.subscribe
    },
    /** @type {typeof updated} */
    updated: stores$1.updated
  };
};
const page = {
  subscribe(fn) {
    const store = getStores().page;
    return store.subscribe(fn);
  }
};
function Card($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let alt;
    let card = $$props["card"];
    let selectable = fallback($$props["selectable"], false);
    let selected = fallback($$props["selected"], false);
    let capturable = fallback($$props["capturable"], false);
    let pending = fallback($$props["pending"], false);
    let animateIn = fallback($$props["animateIn"], false);
    alt = `${card.value} di ${card.suit}`;
    if (animateIn) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div><button${attr_class("card svelte-1udyrqm", void 0, {
        "selectable": selectable,
        "selected": selected,
        "capturable": capturable,
        "pending": pending
      })}${attr("aria-label", alt)}${attr("disabled", !selectable && !capturable && !pending, true)}><img${attr("src", card.image_url)}${attr("alt", alt)} draggable="false" class="svelte-1udyrqm"/></button></div>`);
    } else {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<button${attr_class("card svelte-1udyrqm", void 0, {
        "selectable": selectable,
        "selected": selected,
        "capturable": capturable,
        "pending": pending
      })}${attr("aria-label", alt)}${attr("disabled", !selectable && !capturable && !pending, true)}><img${attr("src", card.image_url)}${attr("alt", alt)} draggable="false" class="svelte-1udyrqm"/></button>`);
    }
    $$renderer2.push(`<!--]-->`);
    bind_props($$props, { card, selectable, selected, capturable, pending, animateIn });
  });
}
function CardBack($$renderer, $$props) {
  let stackCount;
  let count = fallback($$props["count"], 0);
  stackCount = Math.min(count, 4);
  $$renderer.push(`<div class="stack svelte-legrwj"${attr("aria-label", `${stringify(count)} card${stringify(count !== 1 ? "s" : "")}`)}><!--[-->`);
  const each_array = ensure_array_like(Array(stackCount));
  for (let i = 0, $$length = each_array.length; i < $$length; i++) {
    each_array[i];
    $$renderer.push(`<div class="back svelte-legrwj"${attr_style(` transform: translate(${stringify(i * 4)}px, ${stringify(i * -3)}px); z-index: ${stringify(i)}; opacity: ${stringify(0.65 + i * 0.12)}; `)}></div>`);
  }
  $$renderer.push(`<!--]--> `);
  if (count > 0) {
    $$renderer.push("<!--[-->");
    $$renderer.push(`<span class="badge svelte-legrwj">${escape_html(count)}</span>`);
  } else {
    $$renderer.push("<!--[!-->");
  }
  $$renderer.push(`<!--]--></div>`);
  bind_props($$props, { count });
}
function GameBoard($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let capturableIds, myScore, oppScore, myInfo, oppInfo, deckLeft, isMyTurnNow;
    let pendingTableIds = /* @__PURE__ */ new Set();
    const SUIT_ICON = { bastoni: "🪵", coppe: "🏆", oro: "🪙", spade: "⚔️" };
    capturableIds = new Set(store_get($$store_subs ??= {}, "$captureOptions", captureOptions).flat());
    if (store_get($$store_subs ??= {}, "$selectedCard", selectedCard) === null) pendingTableIds = /* @__PURE__ */ new Set();
    myScore = store_get($$store_subs ??= {}, "$scores", scores)[store_get($$store_subs ??= {}, "$playerId", playerId)] ?? 0;
    oppScore = store_get($$store_subs ??= {}, "$scores", scores)[store_get($$store_subs ??= {}, "$opponentId", opponentId)] ?? 0;
    myInfo = store_get($$store_subs ??= {}, "$gameState", gameState)?.players?.[store_get($$store_subs ??= {}, "$playerId", playerId)] ?? {};
    oppInfo = store_get($$store_subs ??= {}, "$gameState", gameState)?.players?.[store_get($$store_subs ??= {}, "$opponentId", opponentId)] ?? {};
    store_get($$store_subs ??= {}, "$gameState", gameState)?.phase ?? "playing";
    deckLeft = store_get($$store_subs ??= {}, "$gameState", gameState)?.deck_remaining ?? 0;
    isMyTurnNow = store_get($$store_subs ??= {}, "$isMyTurn", isMyTurn);
    if (!store_get($$store_subs ??= {}, "$gameState", gameState)) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="board-empty svelte-9e286u"></div>`);
    } else {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<div class="board svelte-9e286u"><div class="zone opponent-zone svelte-9e286u"><div class="player-bar svelte-9e286u"><span class="player-name svelte-9e286u">Opponent</span> <div class="stats svelte-9e286u"><span class="svelte-9e286u">📦 ${escape_html(oppInfo.captured_count ?? 0)}</span> <span class="svelte-9e286u">🧹 ${escape_html(oppInfo.scopas ?? 0)}</span> <span class="pts svelte-9e286u">${escape_html(oppScore)} pts</span></div> `);
      if (store_get($$store_subs ??= {}, "$gameState", gameState) && !isMyTurnNow) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<span class="badge thinking svelte-9e286u">thinking…</span>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--></div> <div class="hand-row svelte-9e286u">`);
      CardBack($$renderer2, { count: oppInfo.hand_count ?? 0 });
      $$renderer2.push(`<!----></div></div> <div class="zone table-zone svelte-9e286u"><div class="zone-header svelte-9e286u"><span class="zone-label svelte-9e286u">Table</span> <span class="deck-pill svelte-9e286u">🂠 ${escape_html(deckLeft)} in deck</span></div> <div class="card-row table-cards svelte-9e286u"><!--[-->`);
      const each_array = ensure_array_like(store_get($$store_subs ??= {}, "$tableCards", tableCards));
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        let card = each_array[$$index];
        Card($$renderer2, {
          card,
          capturable: !!store_get($$store_subs ??= {}, "$selectedCard", selectedCard) && isMyTurnNow && capturableIds.has(card.id) && !pendingTableIds.has(card.id),
          pending: !!store_get($$store_subs ??= {}, "$selectedCard", selectedCard) && isMyTurnNow && pendingTableIds.has(card.id),
          animateIn: true
        });
      }
      $$renderer2.push(`<!--]--> `);
      if (store_get($$store_subs ??= {}, "$tableCards", tableCards).length === 0) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<span class="empty svelte-9e286u">Table is empty</span>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--></div></div> `);
      if (store_get($$store_subs ??= {}, "$lastScopaBy", lastScopaBy)) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div${attr_class("scopa-toast svelte-9e286u", void 0, {
          "scopa-mine": store_get($$store_subs ??= {}, "$lastScopaBy", lastScopaBy).is_mine
        })}>🧹 ${escape_html(store_get($$store_subs ??= {}, "$lastScopaBy", lastScopaBy).is_mine ? "¡Scopa!" : "Scopa del oponente!")}</div>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--> `);
      if (store_get($$store_subs ??= {}, "$errorMessage", errorMessage)) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="error-banner svelte-9e286u" role="alert">⚠️ ${escape_html(store_get($$store_subs ??= {}, "$errorMessage", errorMessage))}</div>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--> `);
      if (store_get($$store_subs ??= {}, "$roundResult", roundResult)) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="overlay svelte-9e286u" role="dialog" aria-modal="true"><div class="result-card svelte-9e286u"><div class="result-icon svelte-9e286u">🎉</div> <h2 class="svelte-9e286u">Round ${escape_html(store_get($$store_subs ??= {}, "$roundResult", roundResult).round_number)} complete</h2> <div class="result-rows svelte-9e286u"><div class="result-row svelte-9e286u"><span class="svelte-9e286u">You</span> <span class="gain svelte-9e286u">+${escape_html(store_get($$store_subs ??= {}, "$roundResult", roundResult).round_scores?.[store_get($$store_subs ??= {}, "$playerId", playerId)] ?? 0)} pts</span></div> <div class="result-row svelte-9e286u"><span class="svelte-9e286u">Opponent</span> <span class="gain svelte-9e286u">+${escape_html(store_get($$store_subs ??= {}, "$roundResult", roundResult).round_scores?.[store_get($$store_subs ??= {}, "$opponentId", opponentId)] ?? 0)} pts</span></div></div> <p class="cumul svelte-9e286u">Total — You: <strong class="svelte-9e286u">${escape_html(store_get($$store_subs ??= {}, "$roundResult", roundResult).cumulative?.[store_get($$store_subs ??= {}, "$playerId", playerId)] ?? 0)}</strong>  | 
                    Opp: <strong class="svelte-9e286u">${escape_html(store_get($$store_subs ??= {}, "$roundResult", roundResult).cumulative?.[store_get($$store_subs ??= {}, "$opponentId", opponentId)] ?? 0)}</strong></p> <p class="next-hint svelte-9e286u">Next round starting…</p></div></div>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--> <div class="zone player-zone svelte-9e286u"><div class="player-bar svelte-9e286u"><span class="player-name svelte-9e286u">You</span> <div class="stats svelte-9e286u"><span class="svelte-9e286u">📦 ${escape_html(myInfo.captured_count ?? 0)}</span> <span class="svelte-9e286u">🧹 ${escape_html(myInfo.scopas ?? 0)}</span> <span class="pts svelte-9e286u">${escape_html(myScore)} pts</span></div> `);
      if (isMyTurnNow) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<span class="badge your-turn svelte-9e286u">Your turn ✨</span>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--></div> <div class="card-row hand-row svelte-9e286u"><!--[-->`);
      const each_array_1 = ensure_array_like(store_get($$store_subs ??= {}, "$myHand", myHand));
      for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
        let card = each_array_1[$$index_1];
        Card($$renderer2, {
          card,
          selectable: isMyTurnNow,
          selected: store_get($$store_subs ??= {}, "$selectedCard", selectedCard)?.id === card.id,
          animateIn: true
        });
      }
      $$renderer2.push(`<!--]--></div> `);
      if (store_get($$store_subs ??= {}, "$selectedCard", selectedCard) && isMyTurnNow) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="capture-hint svelte-9e286u">`);
        if (store_get($$store_subs ??= {}, "$captureOptions", captureOptions).length > 0 && pendingTableIds.size > 0) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<span class="hint-text svelte-9e286u">Tap more cards to complete the combination, or tap a selected card to undo</span>`);
        } else if (store_get($$store_subs ??= {}, "$captureOptions", captureOptions).length > 0) {
          $$renderer2.push("<!--[1-->");
          $$renderer2.push(`<span class="hint-text svelte-9e286u">Tap a glowing card on the table to capture ✨</span>`);
        } else if (store_get($$store_subs ??= {}, "$capturesLoaded", capturesLoaded)) {
          $$renderer2.push("<!--[2-->");
          $$renderer2.push(`<span class="hint-discard svelte-9e286u">No captures — tap your card again to discard</span>`);
        } else {
          $$renderer2.push("<!--[!-->");
          $$renderer2.push(`<span class="hint-text svelte-9e286u">${escape_html(SUIT_ICON[store_get($$store_subs ??= {}, "$selectedCard", selectedCard).suit] ?? "")} ${escape_html(store_get($$store_subs ??= {}, "$selectedCard", selectedCard).value)} selected — tap again to discard if no captures</span>`);
        }
        $$renderer2.push(`<!--]--> <button class="btn-cancel svelte-9e286u" aria-label="Cancel">✕</button></div>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--></div></div>`);
    }
    $$renderer2.push(`<!--]-->`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
function DealAnimation($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let round = fallback(
      $$props["round"],
      1
      // shown as "Round N"
    );
    let type = fallback(
      $$props["type"],
      "full"
      // 'full' = 4-table + 3+3 hands | 'hands' = 3+3 hands only
    );
    const SEQUENCE_FULL = [
      { dest: "table", idx: 0 },
      { dest: "table", idx: 1 },
      { dest: "table", idx: 2 },
      { dest: "table", idx: 3 },
      { dest: "player", idx: 0 },
      { dest: "opponent", idx: 0 },
      { dest: "player", idx: 1 },
      { dest: "opponent", idx: 1 },
      { dest: "player", idx: 2 },
      { dest: "opponent", idx: 2 }
    ];
    const SEQUENCE_HANDS = [
      { dest: "player", idx: 0 },
      { dest: "opponent", idx: 0 },
      { dest: "player", idx: 1 },
      { dest: "opponent", idx: 1 },
      { dest: "player", idx: 2 },
      { dest: "opponent", idx: 2 }
    ];
    const SEQUENCE = type === "hands" ? SEQUENCE_HANDS : SEQUENCE_FULL;
    const DEAL_INTERVAL = 130;
    const CARD_DURATION = 500;
    function getTranslate(dest, idx) {
      switch (dest) {
        case "table":
          return { tx: `${(idx - 1.5) * 80}px`, ty: `0px` };
        case "opponent":
          return { tx: `${(idx - 1) * 72}px`, ty: `-42vh` };
        case "player":
          return { tx: `${(idx - 1) * 72}px`, ty: `42vh` };
      }
    }
    let cards = SEQUENCE.map((item, i) => ({
      ...item,
      ...getTranslate(item.dest, item.idx),
      flying: false,
      landed: false,
      delay: i * DEAL_INTERVAL
    }));
    let deckGlow = false;
    $$renderer2.push(`<div class="overlay svelte-atckps"><div class="round-label svelte-atckps">Round ${escape_html(round)}</div> <div class="zone-hint top svelte-atckps">Opponent</div> `);
    if (type === "full") {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="zone-hint mid svelte-atckps">Table</div>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <div class="zone-hint bot svelte-atckps">You</div> <div${attr_class("deck svelte-atckps", void 0, { "glow": deckGlow })}><!--[-->`);
    const each_array = ensure_array_like([4, 3, 2, 1, 0]);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let z = each_array[$$index];
      $$renderer2.push(`<div class="deck-card svelte-atckps"${attr_style(`transform: translate(${stringify(z * 1.5)}px, ${stringify(-z * 1.5)}px)`)}></div>`);
    }
    $$renderer2.push(`<!--]--></div> <!--[-->`);
    const each_array_1 = ensure_array_like(cards);
    for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
      let card = each_array_1[$$index_1];
      $$renderer2.push(`<div${attr_class("flying-card svelte-atckps", void 0, { "fly": card.flying, "landed": card.landed })}${attr_style(`--tx:${stringify(card.tx)}; --ty:${stringify(card.ty)}; --dur:${stringify(CARD_DURATION)}ms;`)}></div>`);
    }
    $$renderer2.push(`<!--]--></div>`);
    bind_props($$props, { round, type });
  });
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let isConnecting, isWaitingForOpponent, isDisconnected;
    store_get($$store_subs ??= {}, "$page", page).params.session_id;
    onDestroy(() => {
    });
    isConnecting = store_get($$store_subs ??= {}, "$wsStatus", wsStatus) === "connecting";
    isWaitingForOpponent = store_get($$store_subs ??= {}, "$wsStatus", wsStatus) === "waiting" || store_get($$store_subs ??= {}, "$isWaiting", isWaiting);
    store_get($$store_subs ??= {}, "$wsStatus", wsStatus) === "connected" && store_get($$store_subs ??= {}, "$gameState", gameState) !== null;
    isDisconnected = store_get($$store_subs ??= {}, "$wsStatus", wsStatus) === "disconnected";
    head("7np8yw", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Scopa · Game</title>`);
      });
    });
    if (isConnecting) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="overlay svelte-7np8yw"><div class="spinner svelte-7np8yw"></div> <p>Connecting…</p></div>`);
    } else if (isWaitingForOpponent) {
      $$renderer2.push("<!--[1-->");
      $$renderer2.push(`<div class="overlay svelte-7np8yw"><div class="lobby svelte-7np8yw"><div class="lobby-icon svelte-7np8yw">🃏</div> <h2 class="svelte-7np8yw">Waiting for opponent</h2> `);
      if (store_get($$store_subs ??= {}, "$joinCode", joinCode)) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<p class="hint svelte-7np8yw">Share this code with your friend:</p> <div class="join-code svelte-7np8yw">${escape_html(store_get($$store_subs ??= {}, "$joinCode", joinCode))}</div> <button class="btn-copy svelte-7np8yw">${escape_html("📋 Copy Code")}</button>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--> <p class="sub-hint svelte-7np8yw">The game starts automatically when they connect.</p> <div class="spinner-sm svelte-7np8yw"></div></div></div>`);
    } else if (isDisconnected && !store_get($$store_subs ??= {}, "$gameState", gameState)) {
      $$renderer2.push("<!--[2-->");
      $$renderer2.push(`<div class="overlay svelte-7np8yw"><div class="lobby svelte-7np8yw"><div class="lobby-icon svelte-7np8yw">⚡</div> <h2 class="svelte-7np8yw">Disconnected</h2> <p class="hint svelte-7np8yw">The connection was lost.</p> <button class="btn-home svelte-7np8yw">← Home</button></div></div>`);
    } else {
      $$renderer2.push("<!--[!-->");
      if (store_get($$store_subs ??= {}, "$isDealing", isDealing)) {
        $$renderer2.push("<!--[-->");
        DealAnimation($$renderer2, {
          round: store_get($$store_subs ??= {}, "$roundNumber", roundNumber),
          type: store_get($$store_subs ??= {}, "$dealType", dealType)
        });
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--> `);
      if (!store_get($$store_subs ??= {}, "$isDealing", isDealing) || store_get($$store_subs ??= {}, "$gameState", gameState)) {
        $$renderer2.push("<!--[-->");
        GameBoard($$renderer2);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]-->`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
