export const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set(["assets/napolitane/bastoni/10_bastoni.png","assets/napolitane/bastoni/1_bastoni.png","assets/napolitane/bastoni/2_bastoni.png","assets/napolitane/bastoni/3_bastoni.png","assets/napolitane/bastoni/4_bastoni.png","assets/napolitane/bastoni/5_bastoni.png","assets/napolitane/bastoni/6_bastoni.png","assets/napolitane/bastoni/7_bastoni.png","assets/napolitane/bastoni/8_bastoni.png","assets/napolitane/bastoni/9_bastoni.png","assets/napolitane/coppe/10_coppe.png","assets/napolitane/coppe/1_coppe.png","assets/napolitane/coppe/2_coppe.png","assets/napolitane/coppe/3_coppe.png","assets/napolitane/coppe/4_coppe.png","assets/napolitane/coppe/5_coppe.png","assets/napolitane/coppe/6_coppe.png","assets/napolitane/coppe/7_coppe.png","assets/napolitane/coppe/8_coppe.png","assets/napolitane/coppe/9_coppe.png","assets/napolitane/metadata.json","assets/napolitane/oro/10_oro.png","assets/napolitane/oro/1_oro.png","assets/napolitane/oro/2_oro.png","assets/napolitane/oro/3_oro.png","assets/napolitane/oro/4_oro.png","assets/napolitane/oro/5_oro.png","assets/napolitane/oro/6_oro.png","assets/napolitane/oro/7_oro.png","assets/napolitane/oro/8_oro.png","assets/napolitane/oro/9_oro.png","assets/napolitane/spade/10_spade.png","assets/napolitane/spade/1_spade.png","assets/napolitane/spade/2_spade.png","assets/napolitane/spade/3_spade.png","assets/napolitane/spade/4_spade.png","assets/napolitane/spade/5_spade.png","assets/napolitane/spade/6_spade.png","assets/napolitane/spade/7_spade.png","assets/napolitane/spade/8_spade.png","assets/napolitane/spade/9_spade.png","assets/reverso.png"]),
	mimeTypes: {".png":"image/png",".json":"application/json"},
	_: {
		client: {start:"_app/immutable/entry/start.C6BsHrp_.js",app:"_app/immutable/entry/app.BEm_w4hk.js",imports:["_app/immutable/entry/start.C6BsHrp_.js","_app/immutable/chunks/C54pvyWc.js","_app/immutable/chunks/DtFH08mZ.js","_app/immutable/chunks/DRUbZCeC.js","_app/immutable/entry/app.BEm_w4hk.js","_app/immutable/chunks/DtFH08mZ.js","_app/immutable/chunks/BSBlUjVE.js","_app/immutable/chunks/Bwf9qTKs.js","_app/immutable/chunks/DRUbZCeC.js","_app/immutable/chunks/CSHLn78M.js","_app/immutable/chunks/CEAuuTM4.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./nodes/0.js')),
			__memo(() => import('./nodes/1.js')),
			__memo(() => import('./nodes/2.js')),
			__memo(() => import('./nodes/3.js'))
		],
		remotes: {
			
		},
		routes: [
			{
				id: "/",
				pattern: /^\/$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			},
			{
				id: "/game/[session_id]",
				pattern: /^\/game\/([^/]+?)\/?$/,
				params: [{"name":"session_id","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 3 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();
