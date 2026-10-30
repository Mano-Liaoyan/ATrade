// Vitest runs the tests of the assistant service. Node.js runs src/ directly (type stripping), so there is no build.
import { defineConfig } from 'vite-plus';

export default defineConfig({
  test: { include: ['tests/**/*.test.ts'], environment: 'node' },
});
