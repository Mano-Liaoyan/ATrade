import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '..');
const cssPath = path.join(root, 'app', 'globals.css');
const railPath = path.join(root, 'components', 'terminal', 'TerminalModuleRail.tsx');
const registryPath = path.join(root, 'lib', 'terminalModuleRegistry.ts');

test('collapsed module rail keeps icons centered in stable targets while owning vertical overflow', async () => {
  const css = await readFile(cssPath, 'utf8');

  assertCssRuleContains(css, '.terminal-module-rail', [
    '--terminal-rail-collapsed-target: 2.75rem',
    '--terminal-rail-focus-reserve: 0.25rem',
    '--terminal-rail-scrollbar-reserve: 0.85rem',
    'grid-template-rows: auto minmax(0, 1fr)',
    'max-block-size: 100%',
    'min-height: 0',
    'overflow: hidden',
  ]);
  assertCssRuleContains(css, '.terminal-module-rail__navigation', [
    'min-height: 0',
    'overflow: auto',
  ]);
  assertCssRuleContains(css, '.terminal-module-rail--collapsed', [
    'inline-size: var(--terminal-rail-collapsed-inline-size)',
    'min-inline-size: var(--terminal-rail-collapsed-inline-size)',
  ]);
  assertCssRuleContains(css, '.terminal-module-rail--collapsed .terminal-module-rail__navigation', [
    'justify-items: center',
    'overflow-x: hidden',
    'overflow-y: auto',
    'padding-block: var(--terminal-rail-focus-reserve)',
    'padding-inline: var(--terminal-rail-focus-reserve) calc(var(--terminal-rail-scrollbar-reserve) + var(--terminal-rail-focus-reserve))',
    'scroll-padding-block: var(--terminal-rail-focus-reserve)',
  ]);
  assertCssRuleContains(css, '.terminal-module-rail--collapsed .terminal-module-rail__item', [
    'grid-template-columns: 1fr',
    'inline-size: var(--terminal-rail-collapsed-target)',
    'min-block-size: var(--terminal-rail-collapsed-target)',
    'place-items: center',
    'padding: 0',
  ]);
  assertCssRuleContains(css, '.terminal-module-rail--collapsed .terminal-module-rail__short', [
    'inline-size: 2rem',
    'block-size: 2rem',
    'min-height: 0',
  ]);
  assertCssRuleContains(css, '.terminal-module-rail--collapsed .terminal-module-rail__toggle', [
    'inline-size: var(--terminal-rail-collapsed-target)',
    'min-block-size: var(--terminal-rail-collapsed-target)',
    'place-items: center',
  ]);
});

test('collapsed module rail preserves labels, focusable states, disabled tooltips, and late disabled modules', async () => {
  const [css, railSource, registrySource] = await Promise.all([
    readFile(cssPath, 'utf8'),
    readFile(railPath, 'utf8'),
    readFile(registryPath, 'utf8'),
  ]);

  assert.match(railSource, /aria-label=\{isCollapsed \? "Expand module rail" : "Collapse module rail"\}/);
  assert.match(railSource, /title=\{isCollapsed \? module\.label : undefined\}/);
  assert.match(railSource, /aria-disabled="true"/);
  assert.match(railSource, /title=\{`\$\{unavailable\.title\}: \$\{unavailable\.message\}`\}/);
  assert.match(railSource, /data-scroll-owner="module-rail"/);

  assert.match(css, /\.terminal-module-rail--collapsed \.terminal-module-rail__label,\s*\.terminal-module-rail--collapsed \.terminal-module-rail__toggle-label\s*\{[^}]*position:\s*absolute[^}]*clip:\s*rect\(0, 0, 0, 0\)/m);
  assert.doesNotMatch(css, /terminal-module-rail--collapsed[^{}]*terminal-module-rail__(?:label|toggle-label)[^{]*\{[^}]*display:\s*none/i);

  const nodeIndex = registrySource.indexOf('id: "NODE"');
  const ordersIndex = registrySource.indexOf('id: "ORDERS"');
  assert.ok(nodeIndex > -1, 'NODE should remain a visible-disabled rail entry');
  assert.ok(ordersIndex > -1, 'ORDERS should remain a visible-disabled rail entry');
  assert.ok(nodeIndex < ordersIndex, 'NODE and ORDERS should remain in late-list order for overflow reachability coverage');
});

function assertCssRuleContains(css, selector, declarations) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const matches = [...css.matchAll(new RegExp(`${escapedSelector}\\s*\\{(?<body>[^}]*)\\}`, 'gm'))];
  assert.ok(matches.length > 0, `Expected CSS rule for ${selector}`);

  const normalizedBodies = matches.map((match) => match.groups.body.replace(/\s+/g, ' ').trim());
  for (const declaration of declarations) {
    assert.ok(
      normalizedBodies.some((body) => body.includes(declaration)),
      `Expected ${selector} to include "${declaration}". Rules were: ${normalizedBodies.join(' || ')}`,
    );
  }
}
