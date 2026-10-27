// Readability rules (#36) for TypeScript and Svelte. Covers src/, *.test.ts and e2e/ (#39).
import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import svelte from 'eslint-plugin-svelte';
import globals from 'globals';
import ts from 'typescript-eslint';

const MAX_CYCLOMATIC_COMPLEXITY = 10;
const MAX_NESTING_DEPTH = 4;
const MAX_PARAMETERS = 5;
const MAX_STATEMENTS_PER_FUNCTION = 50;
const MAX_LINES_PER_FILE = 1000;

// F2: import a capability as #lib/<capability> and a foundation module as #lib/foundation/<module>.
const PUBLIC_ENTRY_ONLY = {
  regex: '^#lib/(?!foundation/)[^/]+/|^#lib/foundation/[^/]+/',
  message: 'Import the public entry: #lib/<capability> or #lib/foundation/<module>.',
};

// F3: a capability or foundation module imports only #lib/foundation/<module> and the generated API types (#lib/api).
// Only src/routes/ composes capabilities.
const LIB_FOLDERS = ['foundation', 'market_data', 'watchlist', 'strategy', 'backtest', 'paper_trading', 'forward_test'];
const FOUNDATION_ONLY = {
  regex: '^#lib/(?!foundation/|api$)',
  message: 'A capability must not import another capability. Compose capabilities in src/routes/.',
};
const NO_RELATIVE_CROSS_FOLDER = {
  regex: `^(\\.\\./)+(${LIB_FOLDERS.join('|')})(/|$)`,
  message: 'Import another folder of src/lib/ with #lib/.',
};

// B6: these words must not be a part of a name (camelCase, PascalCase or UPPER_CASE word match).
const VAGUE_NAME =
  '^(data|info|manager|helper|utils|handle|process)([A-Z_]|$)' +
  '|(Data|Info|Manager|Helper|Utils|Handle|Process)([A-Z_]|$)' +
  '|(^|_)(DATA|INFO|MANAGER|HELPER|UTILS|HANDLE|PROCESS)(_|$)';

export default defineConfig(
  { ignores: ['build/', '.svelte-kit/', 'src/lib/api/', 'playwright-report/', 'test-results/'] }, // src/lib/api/ is generated (#37).
  js.configs.recommended,
  ts.configs.strictTypeChecked,
  svelte.configs.recommended,
  {
    languageOptions: {
      globals: globals.browser,
      parserOptions: { projectService: true, extraFileExtensions: ['.svelte'] },
    },
  },
  {
    files: ['**/*.svelte', '**/*.svelte.ts'],
    languageOptions: { parserOptions: { parser: ts.parser } },
  },
  {
    rules: {
      complexity: ['error', MAX_CYCLOMATIC_COMPLEXITY], // A1
      'max-depth': ['error', MAX_NESTING_DEPTH], // A2
      '@typescript-eslint/max-params': ['error', { max: MAX_PARAMETERS }], // A3
      'max-statements': ['error', MAX_STATEMENTS_PER_FUNCTION], // A4
      'max-lines': ['error', MAX_LINES_PER_FILE], // A4
      '@typescript-eslint/naming-convention': [
        'error', // B6. A destructured name comes from the source object, for example SvelteKit's `data` prop.
        { selector: 'default', format: null, custom: { regex: VAGUE_NAME, match: false } },
        { selector: 'variable', modifiers: ['destructured'], format: null },
      ],
      '@typescript-eslint/no-magic-numbers': ['error', { ignore: [-1, 0, 1] }], // E9
      'no-implicit-coercion': 'error', // E9
      '@typescript-eslint/strict-boolean-expressions': ['error', { allowNumber: false, allowString: false }], // E9
      'no-restricted-imports': ['error', { patterns: [PUBLIC_ENTRY_ONLY] }], // F2
    },
  },
  {
    files: ['src/lib/**'],
    rules: {
      'no-restricted-imports': [
        'error', // F2, F3. This block replaces the options above, so it repeats PUBLIC_ENTRY_ONLY.
        { patterns: [PUBLIC_ENTRY_ONLY, FOUNDATION_ONLY, NO_RELATIVE_CROSS_FOLDER] },
      ],
    },
  },
  {
    // A test asserts concrete numbers (#39): `expect(bars).toHaveLength(3)` needs no constant.
    files: ['**/*.test.ts', 'e2e/**/*.ts'],
    rules: { '@typescript-eslint/no-magic-numbers': 'off' },
  },
  {
    // The SPA has no server code (#37): no server load, form action, endpoint, server hook or remote function.
    files: ['**/+page.server.*', '**/+layout.server.*', '**/+server.*', '**/hooks.server.*', '**/*.remote.*'],
    rules: {
      'no-restricted-syntax': [
        'error',
        { selector: 'Program', message: 'SvelteKit server features are forbidden. The app is a static SPA.' },
      ],
    },
  },
);
