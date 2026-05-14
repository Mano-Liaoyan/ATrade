import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '..');

const affectedSurfaces = [
  'components/terminal/TerminalChartLandingModule.tsx',
  'components/terminal/TerminalChartWorkspace.tsx',
  'components/terminal/TerminalInstrumentHeader.tsx',
  'components/terminal/TerminalAnalysisWorkspace.tsx',
  'components/terminal/TerminalStatusModule.tsx',
  'components/terminal/TerminalHelpModule.tsx',
  'components/terminal/TerminalProviderDiagnostics.tsx',
  'components/terminal/TerminalDisabledModule.tsx',
  'lib/terminalAnalysisWorkflow.ts',
  'lib/terminalChartWorkspaceWorkflow.ts',
  'lib/terminalModuleRegistry.ts',
];

const removedTutorialFragments = [
  'Discovery and runs stay behind ATrade.Api analysis contracts',
  'Provider-neutral analysis uses ATrade.Api /api/analysis/engines',
  'hover the stock ID/source chips for identity, source, range, cache, and fallback details',
  'The provider returned no candle rows for this lookback range; no synthetic chart data is shown.',
  'Load backend-owned watchlist pins, select a stored stock',
  'Diagnostics surface provider readiness and source labels without credential fields',
  'All browser-visible data flows through ATrade.Api; the frontend does not connect directly',
  'This surface is intentionally empty',
  'The workspace does not show',
  'No committed AI assistant, model runtime, tool-use backend, or retrieval contract exists',
];

const unavailableLabels = [
  'provider-not-configured',
  'provider-unavailable',
  'authentication-required',
  'analysis-engine-not-configured',
  'analysis-engine-unavailable',
  'empty candles',
  'rate-limited',
  'storage failures',
  'disabled module',
  'fallback',
];

test('terminal copy is concise while preserving actionable unavailable-state labels', async () => {
  const source = await readAffectedSurfaceSource();

  for (const fragment of removedTutorialFragments) {
    assert.doesNotMatch(source, new RegExp(escapeRegExp(fragment)), `removed tutorial/internal copy should stay out of active surfaces: ${fragment}`);
  }

  for (const label of unavailableLabels) {
    assert.match(source, new RegExp(escapeRegExp(label), 'i'), `expected concise unavailable-state label: ${label}`);
  }
});

async function readAffectedSurfaceSource() {
  const files = await Promise.all(
    affectedSurfaces.map(async (relativePath) => {
      const contents = await readFile(path.join(root, relativePath), 'utf8');
      return `\n// ${relativePath}\n${contents}`;
    }),
  );

  return files.join('\n');
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
