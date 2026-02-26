import { i as derived, w as writable } from "./exports.js";
const playerId = writable(null);
const opponentId = writable(null);
const joinCode = writable(null);
const wsStatus = writable("disconnected");
const gameState = writable(null);
const selectedCard = writable(null);
const captureOptions = writable([]);
const roundResult = writable(null);
const errorMessage = writable(null);
const isWaiting = writable(false);
const isDealing = writable(false);
const roundNumber = writable(1);
const dealType = writable("full");
const capturesLoaded = writable(false);
const lastScopaBy = writable(null);
const isMyTurn = derived(
  [gameState],
  ([$gs]) => $gs?.is_human_turn ?? false
);
const myHand = derived(
  [gameState],
  ([$gs]) => $gs?.human_hand ?? []
);
const tableCards = derived(
  [gameState],
  ([$gs]) => $gs?.table ?? []
);
derived(
  [gameState],
  ([$gs]) => $gs?.deck_remaining ?? 0
);
const scores = derived(
  [gameState],
  ([$gs]) => $gs?.scores ?? {}
);
export {
  scores as a,
  capturesLoaded as b,
  captureOptions as c,
  isWaiting as d,
  errorMessage as e,
  isDealing as f,
  gameState as g,
  dealType as h,
  isMyTurn as i,
  joinCode as j,
  roundNumber as k,
  lastScopaBy as l,
  myHand as m,
  opponentId as o,
  playerId as p,
  roundResult as r,
  selectedCard as s,
  tableCards as t,
  wsStatus as w
};
