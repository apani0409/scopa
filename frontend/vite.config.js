import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
    plugins: [sveltekit()],

    server: {
        // In development, proxy API and WS calls to the FastAPI backend.
        proxy: {
            '/api': {
                target:       'http://localhost:8000',
                changeOrigin: true,
            },
            '/ws': {
                target:    'ws://localhost:8000',
                ws:        true,
            },
            '/assets': {
                target:       'http://localhost:8000',
                changeOrigin: true,
            },
        },
    },
});
