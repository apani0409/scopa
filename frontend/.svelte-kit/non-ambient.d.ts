
// this file is generated — do not edit it


declare module "svelte/elements" {
	export interface HTMLAttributes<T> {
		'data-sveltekit-keepfocus'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-noscroll'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-preload-code'?:
			| true
			| ''
			| 'eager'
			| 'viewport'
			| 'hover'
			| 'tap'
			| 'off'
			| undefined
			| null;
		'data-sveltekit-preload-data'?: true | '' | 'hover' | 'tap' | 'off' | undefined | null;
		'data-sveltekit-reload'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-replacestate'?: true | '' | 'off' | undefined | null;
	}
}

export {};


declare module "$app/types" {
	export interface AppTypes {
		RouteId(): "/" | "/game" | "/game/[session_id]";
		RouteParams(): {
			"/game/[session_id]": { session_id: string }
		};
		LayoutParams(): {
			"/": { session_id?: string };
			"/game": { session_id?: string };
			"/game/[session_id]": { session_id: string }
		};
		Pathname(): "/" | `/game/${string}` & {};
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): "/assets/napolitane/bastoni/10_bastoni.png" | "/assets/napolitane/bastoni/1_bastoni.png" | "/assets/napolitane/bastoni/2_bastoni.png" | "/assets/napolitane/bastoni/3_bastoni.png" | "/assets/napolitane/bastoni/4_bastoni.png" | "/assets/napolitane/bastoni/5_bastoni.png" | "/assets/napolitane/bastoni/6_bastoni.png" | "/assets/napolitane/bastoni/7_bastoni.png" | "/assets/napolitane/bastoni/8_bastoni.png" | "/assets/napolitane/bastoni/9_bastoni.png" | "/assets/napolitane/coppe/10_coppe.png" | "/assets/napolitane/coppe/1_coppe.png" | "/assets/napolitane/coppe/2_coppe.png" | "/assets/napolitane/coppe/3_coppe.png" | "/assets/napolitane/coppe/4_coppe.png" | "/assets/napolitane/coppe/5_coppe.png" | "/assets/napolitane/coppe/6_coppe.png" | "/assets/napolitane/coppe/7_coppe.png" | "/assets/napolitane/coppe/8_coppe.png" | "/assets/napolitane/coppe/9_coppe.png" | "/assets/napolitane/metadata.json" | "/assets/napolitane/oro/10_oro.png" | "/assets/napolitane/oro/1_oro.png" | "/assets/napolitane/oro/2_oro.png" | "/assets/napolitane/oro/3_oro.png" | "/assets/napolitane/oro/4_oro.png" | "/assets/napolitane/oro/5_oro.png" | "/assets/napolitane/oro/6_oro.png" | "/assets/napolitane/oro/7_oro.png" | "/assets/napolitane/oro/8_oro.png" | "/assets/napolitane/oro/9_oro.png" | "/assets/napolitane/spade/10_spade.png" | "/assets/napolitane/spade/1_spade.png" | "/assets/napolitane/spade/2_spade.png" | "/assets/napolitane/spade/3_spade.png" | "/assets/napolitane/spade/4_spade.png" | "/assets/napolitane/spade/5_spade.png" | "/assets/napolitane/spade/6_spade.png" | "/assets/napolitane/spade/7_spade.png" | "/assets/napolitane/spade/8_spade.png" | "/assets/napolitane/spade/9_spade.png" | "/assets/reverso.png" | string & {};
	}
}