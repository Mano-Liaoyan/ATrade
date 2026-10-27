// Playwright runs e2e/*.spec.ts against backend/tests/e2e_server.py, which serves the built SPA with fakes.
// Run `vp build` first. ATRADE_TEST_DATABASE_URL must point to a PostgreSQL database.
import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

// ATRADE_E2E_PORT lets parallel checkouts run the e2e tests at the same time.
const E2E_PORT = process.env['ATRADE_E2E_PORT'] ?? '4173';
const BACKEND_DIR = path.resolve(import.meta.dirname, '../backend');
const BUILD_DIR = path.resolve(import.meta.dirname, 'build');

export default defineConfig({
  testDir: 'e2e',
  forbidOnly: process.env['CI'] !== undefined,
  reporter: 'list',
  use: { baseURL: `http://127.0.0.1:${E2E_PORT}` },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'msedge', use: { ...devices['Desktop Edge'], channel: 'msedge' } },
  ],
  webServer: {
    command: 'uv run python -m tests.e2e_server',
    cwd: BACKEND_DIR,
    url: `http://127.0.0.1:${E2E_PORT}/api/health`,
    reuseExistingServer: false,
    env: { ATRADE_E2E_PORT: E2E_PORT, ATRADE_E2E_FRONTEND_BUILD_DIR: BUILD_DIR },
  },
});
