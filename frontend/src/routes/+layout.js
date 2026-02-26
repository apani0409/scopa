// Disable SSR for the entire app — this is a client-side multiplayer game
// with WebSocket state and sessionStorage. SSR would not be meaningful.
export const ssr      = false;
export const prerender = false;
