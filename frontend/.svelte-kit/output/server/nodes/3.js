

export const index = 3;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/game/_session_id_/_page.svelte.js')).default;
export const universal = {
  "ssr": false,
  "prerender": false
};
export const universal_id = "src/routes/game/[session_id]/+page.js";
export const imports = ["_app/immutable/nodes/3.pMJkDlPX.js","_app/immutable/chunks/Bwf9qTKs.js","_app/immutable/chunks/DtFH08mZ.js","_app/immutable/chunks/BbsrXejN.js","_app/immutable/chunks/DRUbZCeC.js","_app/immutable/chunks/BSBlUjVE.js","_app/immutable/chunks/CSHLn78M.js","_app/immutable/chunks/DSjyWIzM.js","_app/immutable/chunks/C1tfcwLj.js","_app/immutable/chunks/CEAuuTM4.js","_app/immutable/chunks/C54pvyWc.js"];
export const stylesheets = ["_app/immutable/assets/3.Bn723ic4.css"];
export const fonts = [];
