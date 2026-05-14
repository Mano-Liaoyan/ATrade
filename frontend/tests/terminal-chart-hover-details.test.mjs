import assert from 'node:assert/strict';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
import ts from 'typescript';

const root = path.resolve(import.meta.dirname, '..');
const detailsPath = path.join(root, 'lib', 'terminalChartHoverDetails.ts');
const headerPath = path.join(root, 'components', 'terminal', 'TerminalInstrumentHeader.tsx');
const workspacePath = path.join(root, 'components', 'terminal', 'TerminalChartWorkspace.tsx');

test('chart identity hover details keep visible labels compact while exposing provider-neutral source/cache context', async () => {
  assert.equal(existsSync(detailsPath), true, 'chart hover details should be built by a public frontend helper');

  const { createTerminalChartHoverDetails } = await importTranspiledModule(detailsPath);
  const details = createTerminalChartHoverDetails({
    candleSource: 'timescale-cache:ibkr-ibeam',
    candleSourceLabel: 'Stale Timescale cache (IBKR/iBeam)',
    candleSourceStatus: {
      freshness: 'stale',
      generatedAtUtc: '2026-05-14T12:00:00.000Z',
      refreshAttemptedAtUtc: '2026-05-14T12:15:00.000Z',
      refreshError: {
        code: 'provider-unavailable',
        message: 'Provider refresh failed.',
      },
      source: 'timescale-cache:ibkr-ibeam',
    },
    fallbackCopy: 'SignalR unavailable: HTTP fallback active.',
    identity: {
      assetClass: 'STK',
      currency: 'USD',
      exchange: 'NASDAQ',
      ibkrConid: 265598,
      provider: 'ibkr',
      providerSymbolId: '265598',
      symbol: 'MSFT',
    },
    indicatorSource: 'timescale-cache:ibkr-ibeam',
    indicatorSourceLabel: 'Stale Timescale cache (IBKR/iBeam)',
    latestUpdateSource: null,
    latestUpdateSourceLabel: null,
    noOrderCopy: 'Read-only chart and analysis. No order controls.',
    rangeDescription: 'Past day from now',
    rangeLabel: '1D',
    streamLabel: 'Stream unavailable',
    streamState: 'unavailable',
    symbol: 'MSFT',
  });

  assert.equal(details.compactIdentityLabel, 'MSFT · IBKR:265598 · NASDAQ · USD · STK');
  assert.equal(details.compactSourceLabel, 'Stale Timescale cache (IBKR/iBeam)');
  assert.equal(details.compactStateLabel, 'Cache stale · stream unavailable');

  const rows = Object.fromEntries(details.rows.map((row) => [row.label, row.value]));
  assert.equal(rows['Exact Instrument Identity'], 'MSFT · IBKR:265598 · NASDAQ · USD · STK');
  assert.equal(rows['Provider symbol id'], '265598 (IBKR conid alias)');
  assert.equal(rows['Original provider source'], 'ibkr-ibeam');
  assert.equal(rows['Cache freshness'], 'stale');
  assert.equal(rows['Lookback range'], '1D — Past day from now');
  assert.match(rows['Fallback state'], /HTTP fallback active/);

  assert.match(details.title, /Original provider source: ibkr-ibeam/);
  assert.doesNotMatch(details.title, /https?:\/\//i);
  assert.doesNotMatch(details.title, /credential|sensitive|provider refresh failed/i);
  assert.doesNotMatch(details.title, /^IBKR conid:/m, 'IBKR conid must remain a provider symbol id alias, not a separate identity dimension');
});

test('chart workspace moves verbose footer identity/source notes into hoverable stock ID/source chips', async () => {
  const headerSource = await readFile(headerPath, 'utf8');
  assert.match(headerSource, /data-testid="chart-identity-hover-details"/);
  assert.match(headerSource, /data-testid="chart-source-hover-details"/);
  assert.match(headerSource, /title=\{chart\.view\.hoverDetailsTitle\}/);
  assert.match(headerSource, /chart\.view\.compactIdentityLabel/);
  assert.match(headerSource, /chart\.view\.compactSourceLabel/);

  const workspaceSource = await readFile(workspacePath, 'utf8');
  assert.match(workspaceSource, /chart-footer-note--compact/);
  assert.match(workspaceSource, /details are on the identity and source chips/);
  assert.doesNotMatch(workspaceSource, /<p>\{chart\.view\.identitySummary\}<\/p>/);
  assert.doesNotMatch(workspaceSource, /Current candle source:/);
  assert.doesNotMatch(workspaceSource, /Streaming snapshots are unavailable; polling continues/);
});

async function importTranspiledModule(sourcePath) {
  const source = await readFile(sourcePath, 'utf8');
  const transpiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
    fileName: sourcePath,
  });

  const tempRoot = path.join(root, '.test-tmp');
  await mkdir(tempRoot, { recursive: true });
  const tempDir = await mkdtemp(path.join(tempRoot, 'atrade-chart-hover-details-'));
  const outputPath = path.join(tempDir, 'terminalChartHoverDetails.mjs');
  await writeFile(outputPath, transpiled.outputText);

  try {
    return await import(pathToFileURL(outputPath).href);
  } finally {
    await rm(tempDir, { recursive: true, force: true });
  }
}
