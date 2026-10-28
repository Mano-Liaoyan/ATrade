// One CodeMirror theme for the strategy editor and the code diff. It follows the Carbon theme tokens (--cds-*) and the color scheme of the page (foundation/color_scheme: the header theme button and the
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

// The editor parts use the Carbon theme tokens, so they change with the page color scheme without a reconfiguration.
const editorChrome = EditorView.theme({
  '&': {
    color: 'var(--cds-text-primary)',
    backgroundColor: 'var(--cds-layer-01)',
  },
  // The Carbon code-02 type style in the editor and in the code diff (one code size on all pages).
  '.cm-scroller': {
    fontFamily: 'var(--cds-code-02-font-family)',
    fontSize: 'var(--cds-code-02-font-size)',
    lineHeight: 'var(--cds-code-02-line-height)',
  },
  '.cm-content': { caretColor: 'var(--cds-text-primary)' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--cds-text-primary)' },
  '.cm-gutters': {
    color: 'var(--cds-text-secondary)',
    backgroundColor: 'var(--cds-layer-01)',
    borderRight: '1px solid var(--cds-border-subtle-01)',
  },
  '.cm-activeLine': { backgroundColor: 'var(--cds-layer-hover-01)' },
  // CodeMirror draws the selection in a layer below the lines. The opaque line highlight would hide it.
  '&.atrade-has-selection .cm-activeLine': { backgroundColor: 'transparent' },
  '.cm-activeLineGutter': { color: 'var(--cds-text-primary)', backgroundColor: 'var(--cds-layer-hover-01)' },
  '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection':
    { backgroundColor: 'var(--cds-highlight)' },
  '.cm-selectionMatch': { backgroundColor: 'var(--cds-highlight)' },
  '&.cm-focused .cm-matchingBracket': { backgroundColor: 'var(--cds-highlight)', outline: 'none' },
  '.cm-foldPlaceholder': {
    color: 'var(--cds-text-secondary)',
    backgroundColor: 'transparent',
    border: '1px solid var(--cds-border-subtle-01)',
  },
  '.cm-tooltip': {
    color: 'var(--cds-text-primary)',
    backgroundColor: 'var(--cds-layer-01)',
    border: '1px solid var(--cds-border-subtle-01)',
  },
  '.cm-tooltip-autocomplete > ul > li[aria-selected]': {
    color: 'var(--cds-text-primary)',
    backgroundColor: 'var(--cds-highlight)',
  },
  '.cm-panels': { color: 'var(--cds-text-primary)', backgroundColor: 'var(--cds-layer-01)' },
  '.cm-panels-top': { borderBottom: '1px solid var(--cds-border-subtle-01)' },
  '.cm-panels-bottom': { borderTop: '1px solid var(--cds-border-subtle-01)' },
  // Code diff (@codemirror/merge): removed lines on the first side, added lines on the second side.
  '&.cm-merge-a .cm-changedLine, .cm-deletedChunk': { backgroundColor: 'color-mix(in srgb, var(--cds-support-error) 15%, transparent)' },
  '&.cm-merge-b .cm-changedLine': { backgroundColor: 'color-mix(in srgb, var(--cds-support-success) 15%, transparent)' },
  '&.cm-merge-a .cm-changedText, .cm-deletedChunk .cm-deletedText': {
    background: 'color-mix(in srgb, var(--cds-support-error) 40%, transparent)',
  },
  '&.cm-merge-b .cm-changedText': { background: 'color-mix(in srgb, var(--cds-support-success) 40%, transparent)' },
  '&.cm-merge-a .cm-changedLineGutter, .cm-deletedLineGutter': { background: 'var(--cds-support-error)' },
  '&.cm-merge-b .cm-changedLineGutter': { background: 'var(--cds-support-success)' },
  '.cm-collapsedLines': {
    color: 'var(--cds-text-secondary)',
    background: 'var(--cds-background)',
    borderTop: '1px dashed var(--cds-border-subtle-01)',
    borderBottom: '1px dashed var(--cds-border-subtle-01)',
    fontFamily: 'inherit',
    fontSize: 'var(--cds-helper-text-01-font-size)',
  },
  '.cm-collapsedLines:hover': { color: 'var(--cds-text-primary)' },
  // Live type errors (@codemirror/lint) look like a Carbon low-contrast inline notification. They do not block the save.
  '.cm-lintRange-error': { backgroundImage: 'none', textDecoration: 'underline wavy var(--cds-support-error)' },
  '.cm-lintRange-warning': { backgroundImage: 'none', textDecoration: 'underline wavy var(--cds-support-warning)' },
  '.cm-lintRange-info, .cm-lintRange-hint': { backgroundImage: 'none', textDecoration: 'underline wavy var(--cds-support-info)' },
  '.cm-lintRange-active': { backgroundColor: 'var(--cds-highlight)' },
  '.cm-tooltip.cm-tooltip-lint': { border: '1px solid var(--cds-border-subtle-01)' },
  '.cm-diagnostic': {
    padding: 'var(--cds-spacing-03) var(--cds-spacing-05)',
    marginLeft: '0',
    color: 'var(--cds-text-primary)',
    fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
    fontSize: 'var(--cds-body-compact-01-font-size)',
    lineHeight: 'var(--cds-body-compact-01-line-height)',
  },
  '.cm-diagnostic-error': {
    borderLeft: '3px solid var(--cds-support-error)',
    backgroundColor: 'var(--cds-notification-background-error)',
  },
  '.cm-diagnostic-warning': {
    borderLeft: '3px solid var(--cds-support-warning)',
    backgroundColor: 'var(--cds-notification-background-warning)',
  },
  '.cm-diagnostic-info, .cm-diagnostic-hint': {
    borderLeft: '3px solid var(--cds-support-info)',
    backgroundColor: 'var(--cds-notification-background-info)',
  },
  '.cm-diagnosticSource': { color: 'var(--cds-text-secondary)', opacity: '1' },
});

// The editor has the class atrade-has-selection while the main selection is not empty. The theme then removes the
// cursor line highlight, so the selection shows on that line too.
const markSelection = EditorView.editorAttributes.compute(
  ['selection'],
  (state): Record<string, string> => (state.selection.main.empty ? {} : { class: 'atrade-has-selection' }),
);

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
  return [editorChrome, markSelection, schemeCompartment.of(selectSchemeExtensions(isDarkColorScheme())), followScheme];
}
