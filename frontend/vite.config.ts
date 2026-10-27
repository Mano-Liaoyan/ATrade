// SvelteKit 3 reads its configuration here. svelte.config.js is no longer used.
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite-plus';

export default defineConfig({
  plugins: [
    // SPA (#37): the fallback page loads the app for every URL. No server code runs in production.
    sveltekit({ adapter: adapter({ fallback: '200.html' }) }),
  ],
  // `vp dev` sends API and WebSocket requests to a local backend (python -m atrade.app.web).
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/ws': { target: 'ws://127.0.0.1:8000', ws: true } } },
  // Vitest runs *.test.ts. Playwright runs e2e/*.spec.ts (#39).
  test: { include: ['src/**/*.test.ts'] },
});
