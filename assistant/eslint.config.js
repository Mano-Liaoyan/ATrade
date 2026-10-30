// Readability rules (#36) for the TypeScript of the assistant service. The same limits as frontend/eslint.config.js.
import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import globals from 'globals';
import ts from 'typescript-eslint';

const MAX_CYCLOMATIC_COMPLEXITY = 10;
const MAX_NESTING_DEPTH = 4;
const MAX_PARAMETERS = 5;
const MAX_STATEMENTS_PER_FUNCTION = 50;
const MAX_LINES_PER_FILE = 1000;

// B6: these words must not be a part of a name (camelCase, PascalCase or UPPER_CASE word match).
const VAGUE_NAME =
  '^(data|info|manager|helper|utils|handle|process)([A-Z_]|$)' +
  '|(Data|Info|Manager|Helper|Utils|Handle|Process)([A-Z_]|$)' +
  '|(^|_)(DATA|INFO|MANAGER|HELPER|UTILS|HANDLE|PROCESS)(_|$)';

export default defineConfig(
  js.configs.recommended,
  ts.configs.strictTypeChecked,
  {
    languageOptions: {
      globals: globals.node,
      parserOptions: { projectService: true },
    },
  },
  {
    rules: {
      complexity: ['error', MAX_CYCLOMATIC_COMPLEXITY], // A1
      'max-depth': ['error', MAX_NESTING_DEPTH], // A2
      '@typescript-eslint/max-params': ['error', { max: MAX_PARAMETERS }], // A3
      'max-statements': ['error', MAX_STATEMENTS_PER_FUNCTION], // A4
      'max-lines': ['error', MAX_LINES_PER_FILE], // A4
      '@typescript-eslint/naming-convention': [
        'error', // B6. A destructured name comes from the source object.
        { selector: 'default', format: null, custom: { regex: VAGUE_NAME, match: false } },
        { selector: 'variable', modifiers: ['destructured'], format: null },
        // Names of JSON fields that another program defines, for example the OpenAI wire format.
        { selector: ['objectLiteralProperty', 'typeProperty'], modifiers: ['requiresQuotes'], format: null },
        // Option names of the pi SDK (createAgentSession, DefaultResourceLoader).
        {
          selector: 'objectLiteralProperty',
          filter: { regex: '^(sessionManager|settingsManager)$', match: true },
          format: null,
        },
      ],
      '@typescript-eslint/no-magic-numbers': ['error', { ignore: [-1, 0, 1] }], // E9
      'no-implicit-coercion': 'error', // E9
      '@typescript-eslint/strict-boolean-expressions': ['error', { allowNumber: false, allowString: false }], // E9
    },
  },
  {
    // A test asserts concrete numbers (#39).
    files: ['tests/**/*.ts'],
    rules: { '@typescript-eslint/no-magic-numbers': 'off' },
  },
  {
    files: ['eslint.config.js'],
    ...ts.configs.disableTypeChecked,
  },
);
