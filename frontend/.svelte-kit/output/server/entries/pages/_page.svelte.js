import { h as head } from "../../chunks/index.js";
import "@sveltejs/kit/internal";
import "../../chunks/exports.js";
import "../../chunks/utils.js";
import "clsx";
import "@sveltejs/kit/internal/server";
import "../../chunks/root.js";
import "../../chunks/state.svelte.js";
import "../../chunks/game.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    head("1uha8ag", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Scopa</title>`);
      });
    });
    $$renderer2.push(`<main class="home svelte-1uha8ag"><div class="hero svelte-1uha8ag"><div class="logo svelte-1uha8ag">🃏</div> <h1 class="svelte-1uha8ag">Scopa</h1> <p class="subtitle svelte-1uha8ag">The classic Italian card game — now multiplayer</p></div> `);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="menu svelte-1uha8ag"><button class="btn-primary svelte-1uha8ag">Create Game</button> <button class="btn-secondary svelte-1uha8ag">Join Game</button></div>`);
    }
    $$renderer2.push(`<!--]--></main>`);
  });
}
export {
  _page as default
};
