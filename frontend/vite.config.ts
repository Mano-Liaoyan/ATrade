// SvelteKit 3 reads its configuration here. svelte.config.js is no longer used.
import path from 'node:path';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite-plus';

const NODE_MODULES = path.resolve(import.meta.dirname, 'node_modules');
const CLIENT_TESTS = ['src/routes/run_workbench.svelte.test.ts'];

export default defineConfig({
  plugins: [
    // SPA (#37): the fallback page loads the app for every URL. No server code runs in production.
    sveltekit({ adapter: adapter({ fallback: '200.html' }) }),
  ],
  // Carbon SCSS (src/lib/foundation/carbon/carbon.scss) loads @carbon/themes, @carbon/layout and other packages that
  // are not direct dependencies. pnpm keeps them in node_modules/.pnpm/node_modules.
  css: {
    preprocessorOptions: {
      scss: {
        loadPaths: [NODE_MODULES, path.join(NODE_MODULES, '.pnpm', 'node_modules')],
        // Carbon uses Sass features that Sass deprecates. The warnings are not ATrade's to fix.
        quietDeps: true,
      },
    },
  },
  // `vp dev` sends API and WebSocket requests to a local backend (python -m atrade.app.web).
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/ws': { target: 'ws://127.0.0.1:8000', ws: true } } },
  // Vitest runs *.test.ts. Playwright runs e2e/*.spec.ts (#39). The tests that need $effect run on the client build.
  test: {
    projects: [
      { extends: true, test: { name: 'server', include: ['src/**/*.test.ts'], exclude: CLIENT_TESTS } },
      {
        extends: true,
        environments: { ssr: { consumer: 'client', resolve: { conditions: ['browser'] } } },
        test: { name: 'client', include: CLIENT_TESTS },
      },
    ],
  },
});
