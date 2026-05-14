import assert from 'node:assert/strict';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

const root = path.resolve(import.meta.dirname, '..');
const componentPath = path.join(root, 'components', 'terminal', 'TerminalMetadataGrid.tsx');
const cssPath = path.join(root, 'app', 'globals.css');

test('TerminalMetadataGrid keeps compact metadata labels separated from long values', async () => {
  assert.equal(existsSync(componentPath), true, 'TerminalMetadataGrid should provide the shared compact metadata display pattern');

  const { TerminalMetadataGrid } = await importTranspiledComponent(componentPath);
  const html = renderToStaticMarkup(
    React.createElement(TerminalMetadataGrid, {
      ariaLabel: 'Exact Instrument Identity metadata',
      columns: 3,
      items: [
        {
          code: true,
          detail: 'provider-neutral contracts preserve provider, exchange, currency, and asset class.',
          label: 'Exact Instrument Identity',
          value: 'IBKR-CONID-12345678901234567890-NASDAQ-STK-USD',
        },
        {
          detail: 'Saved backtest run metadata keeps the browser-visible source explicit.',
          label: 'paper-capital source',
          value: 'IBKR paper balance · USD',
        },
      ],
    }),
  );

  assert.match(html, /<dl[^>]+aria-label="Exact Instrument Identity metadata"/);
  assert.match(html, /<dt[^>]*>Exact Instrument Identity<\/dt><dd/);
  assert.match(html, /<dt[^>]*>paper-capital source<\/dt><dd/);
  assert.match(html, /<code>IBKR-CONID-12345678901234567890-NASDAQ-STK-USD<\/code>/);
  assert.match(html, /provider-neutral contracts/);
  assert.match(html, /Saved backtest run metadata/);

  const css = await readFile(cssPath, 'utf8');
  assertCssRuleContains(css, '.terminal-metadata-grid__item', ['min-width: 0']);
  assertCssRuleContains(css, '.terminal-metadata-grid__value', [
    'overflow-wrap: anywhere',
    'white-space: normal',
    'word-break: break-word',
  ]);
  assertCssRuleContains(css, '.terminal-metadata-grid__detail', ['overflow-wrap: anywhere']);
});

test('representative workspace metadata summaries use the shared compact metadata contract', async () => {
  const representativeModules = [
    ['analysis workspace', 'components/terminal/TerminalAnalysisWorkspace.tsx'],
    ['backtest workspace', 'components/terminal/TerminalBacktestWorkspace.tsx'],
    ['backtest comparison summary', 'components/terminal/BacktestComparisonPanel.tsx'],
    ['chart Exact Instrument Identity summary', 'components/terminal/TerminalInstrumentHeader.tsx'],
    ['market monitor Exact Instrument Identity summary', 'components/terminal/MarketMonitorDetailPanel.tsx'],
    ['home summary grid', 'components/terminal/TerminalHomeModule.tsx'],
    ['status summary grid', 'components/terminal/TerminalStatusModule.tsx'],
    ['provider diagnostics summary grid', 'components/terminal/TerminalProviderDiagnostics.tsx'],
  ];

  for (const [surface, relativePath] of representativeModules) {
    const source = await readFile(path.join(root, relativePath), 'utf8');
    assert.match(source, /TerminalMetadataGrid/, `${surface} should render compact label/value metadata through the shared grid`);
  }
});

async function importTranspiledComponent(sourcePath) {
  const source = await readFile(sourcePath, 'utf8');
  const transpiled = ts.transpileModule(source, {
    compilerOptions: {
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
    fileName: sourcePath,
  });

  const tempRoot = path.join(root, '.test-tmp');
  await mkdir(tempRoot, { recursive: true });
  const tempDir = await mkdtemp(path.join(tempRoot, 'atrade-metadata-grid-'));
  const outputPath = path.join(tempDir, 'TerminalMetadataGrid.mjs');
  await writeFile(outputPath, transpiled.outputText);

  try {
    return await import(pathToFileURL(outputPath).href);
  } finally {
    await rm(tempDir, { recursive: true, force: true });
  }
}

function assertCssRuleContains(css, selector, declarations) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = css.match(new RegExp(`${escapedSelector}\\s*\\{(?<body>[^}]*)\\}`, 'm'));
  assert.ok(match?.groups?.body, `Expected CSS rule for ${selector}`);

  const normalizedBody = match.groups.body.replace(/\s+/g, ' ').trim();
  for (const declaration of declarations) {
    assert.ok(
      normalizedBody.includes(declaration),
      `Expected ${selector} to include "${declaration}". Rule was: ${normalizedBody}`,
    );
  }
}
