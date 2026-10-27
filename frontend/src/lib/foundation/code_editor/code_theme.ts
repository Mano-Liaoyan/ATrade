// One CodeMirror theme for the strategy editor and the code diff. It follows the app color tokens
// (src/routes/+layout.svelte) and the color scheme of the page (foundation/color_scheme: the header theme button and the
// operating system), in all browsers. Without it, CodeMirror uses its light default theme: a light gutter and
// low-contrast syntax colors on the dark page.
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language';
import { Compartment, type Extension } from '@codemirror/state';
import { EditorView, ViewPlugin } from '@codemirror/view';
import { tags } from '@lezer/highlight';
import { isDarkColorScheme, watchColorScheme } from '#lib/foundation/color_scheme';
import { CODE_COLORS, type CodeColorScheme } from './code_colors';

function createHighlightStyle(colors: CodeColorScheme): HighlightStyle {
  const text = colors.text;
  return HighlightStyle.define([
    { tag: [tags.comment, tags.meta], color: text.comment },
    { tag: [tags.keyword, tags.controlKeyword, tags.definitionKeyword, tags.moduleKeyword, tags.operatorKeyword, tags.modifier], color: text.keyword },
    { tag: [tags.self, tags.bool, tags.null, tags.atom], color: text.number },
    { tag: [tags.string, tags.special(tags.string), tags.docString], color: text.string },
    { tag: [tags.number, tags.constant(tags.variableName), tags.escape], color: text.number },
    { tag: [tags.function(tags.variableName), tags.function(tags.definition(tags.variableName))], color: text.function },
    { tag: [tags.function(tags.propertyName)], color: text.function },
    { tag: [tags.className, tags.definition(tags.className), tags.typeName, tags.namespace], color: text.type },
    { tag: [tags.standard(tags.variableName), tags.special(tags.variableName)], color: text.number },
    { tag: [tags.variableName, tags.propertyName, tags.operator, tags.punctuation], color: text.plain },
    { tag: tags.invalid, color: text.keyword, textDecoration: 'underline' },
  ]);
}

const LIGHT_HIGHLIGHT = createHighlightStyle(CODE_COLORS.light);
const DARK_HIGHLIGHT = createHighlightStyle(CODE_COLORS.dark);

function selectSchemeExtensions(isDark: boolean): Extension {
  // EditorView.darkTheme also selects the dark variants of the CodeMirror base themes (merge view, tooltips, search).
  return [EditorView.darkTheme.of(isDark), syntaxHighlighting(isDark ? DARK_HIGHLIGHT : LIGHT_HIGHLIGHT)];
}

// The editor parts use the app CSS tokens, so they change with the page color scheme without a reconfiguration.
const editorChrome = EditorView.theme({
  '&': {
    color: 'var(--color-text)',
    backgroundColor: 'var(--color-surface)',
  },
  '.cm-content': { caretColor: 'var(--color-text)' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--color-text)' },
  '.cm-gutters': {
    color: 'var(--color-muted)',
    backgroundColor: 'var(--color-surface)',
    borderRight: '1px solid var(--color-border)',
  },
  '.cm-activeLine': { backgroundColor: 'var(--color-code-active-line)' },
  '.cm-activeLineGutter': { color: 'var(--color-text)', backgroundColor: 'var(--color-code-active-line)' },
  '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection':
    { backgroundColor: 'var(--color-code-selection)' },
  '.cm-selectionMatch': { backgroundColor: 'var(--color-code-selection)' },
  '&.cm-focused .cm-matchingBracket': { backgroundColor: 'var(--color-code-selection)', outline: 'none' },
  '.cm-foldPlaceholder': {
    color: 'var(--color-muted)',
    backgroundColor: 'transparent',
    border: '1px solid var(--color-border)',
  },
  '.cm-tooltip': {
    color: 'var(--color-text)',
    backgroundColor: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
  },
  '.cm-tooltip-autocomplete > ul > li[aria-selected]': {
    color: 'var(--color-text)',
    backgroundColor: 'var(--color-code-selection)',
  },
  '.cm-panels': { color: 'var(--color-text)', backgroundColor: 'var(--color-surface)' },
  '.cm-panels-top': { borderBottom: '1px solid var(--color-border)' },
  '.cm-panels-bottom': { borderTop: '1px solid var(--color-border)' },
  // Code diff (@codemirror/merge): removed lines on the first side, added lines on the second side.
  '&.cm-merge-a .cm-changedLine, .cm-deletedChunk': { backgroundColor: 'var(--color-diff-removed-line)' },
  '&.cm-merge-b .cm-changedLine': { backgroundColor: 'var(--color-diff-added-line)' },
  '&.cm-merge-a .cm-changedText, .cm-deletedChunk .cm-deletedText': {
    background: 'var(--color-diff-removed-text)',
    borderRadius: '2px',
  },
  '&.cm-merge-b .cm-changedText': { background: 'var(--color-diff-added-text)', borderRadius: '2px' },
  '&.cm-merge-a .cm-changedLineGutter, .cm-deletedLineGutter': { background: 'var(--color-diff-removed-mark)' },
  '&.cm-merge-b .cm-changedLineGutter': { background: 'var(--color-diff-added-mark)' },
  '.cm-collapsedLines': {
    color: 'var(--color-muted)',
    background: 'var(--color-background)',
    borderTop: '1px dashed var(--color-border)',
    borderBottom: '1px dashed var(--color-border)',
    fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
    fontSize: '0.8125rem',
  },
  '.cm-collapsedLines:hover': { color: 'var(--color-text)' },
});

/** The shared code theme. It reads the color scheme when the editor starts and follows later changes. */
export function createCodeTheme(): Extension {
  const schemeCompartment = new Compartment();
  const followScheme = ViewPlugin.define((view) => {
    const endColorSchemeWatch = watchColorScheme(() => {
      view.dispatch({ effects: schemeCompartment.reconfigure(selectSchemeExtensions(isDarkColorScheme())) });
    });
    return {
      destroy(): void {
        endColorSchemeWatch();
      },
    };
  });
  return [editorChrome, schemeCompartment.of(selectSchemeExtensions(isDarkColorScheme())), followScheme];
}
