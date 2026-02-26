

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_layout.svelte.js')).default;
export const universal = {
  "ssr": false,
  "prerender": false
};
export const universal_id = "src/routes/+layout.js";
export const imports = ["_app/immutable/nodes/0.BnU1srQO.js","_app/immutable/chunks/Bwf9qTKs.js","_app/immutable/chunks/DtFH08mZ.js","_app/immutable/chunks/BbsrXejN.js"];
export const stylesheets = ["_app/immutable/assets/0.0c5GXRld.css"];
export const fonts = [];
