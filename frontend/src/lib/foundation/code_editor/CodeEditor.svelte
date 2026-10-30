<!-- Python code editor: CodeMirror 6 with @codemirror/lang-python. It has no domain meaning (docs/architecture.md section 13).
     `revealLine(line)` (through `bind:this`) puts the cursor at the start of a line, scrolls it into view, and focuses
     the editor, for example from a list of code problems.
     With `readOnly`, the user cannot change the code, the lines wrap, and the editor takes the height of its code, so
     a parent scroll region scrolls it. `highlightedLines` get a neutral background. `scrollLineIntoRegion(line, region)`
     scrolls the region so that the line is near its top, without the page scroll. -->
<script lang="ts">
  import { acceptCompletion } from '@codemirror/autocomplete';
  import { indentWithTab } from '@codemirror/commands';
  import { python } from '@codemirror/lang-python';
  import { EditorState, Prec, RangeSetBuilder, StateEffect, StateField, type Extension } from '@codemirror/state';
  import { Decoration, keymap, type DecorationSet } from '@codemirror/view';
  import { EditorView, basicSetup } from 'codemirror';
  import { createCodeTheme } from './code_theme';

  interface Props {
    code: string;
    label: string;
    onCodeChange: (code: string) => void;
    /** More CodeMirror extensions, for example a language server client. The editor reads them once. */
    extensions?: Extension[];
    /** The editor reads it once. */
    readOnly?: boolean;
    /** Line numbers (1 is the first line) that get a neutral background. */
    highlightedLines?: readonly number[];
  }

  const { code, label, onCodeChange, extensions = [], readOnly = false, highlightedLines = [] }: Props = $props();

  // A line that scrollLineIntoRegion shows is 1 / LINE_POSITION_PARTS of the region height down from its top.
  const LINE_POSITION_PARTS = 3;
  const highlightedLineDecoration = Decoration.line({ class: 'code-editor__highlighted-line' });
  const setHighlightedLines = StateEffect.define<readonly number[]>();
  const highlightedLineField = StateField.define<DecorationSet>({
    create: () => Decoration.none,
    update(decorations, transaction) {
      for (const effect of transaction.effects) {
        if (effect.is(setHighlightedLines)) {
          const builder = new RangeSetBuilder<Decoration>();
          for (const line of effect.value) {
            if (line >= 1 && line <= transaction.state.doc.lines) {
              const position = transaction.state.doc.line(line).from;
              builder.add(position, position, highlightedLineDecoration);
            }
          }
          return builder.finish();
        }
      }
      return decorations.map(transaction.changes);
    },
    provide: (field) => EditorView.decorations.from(field),
  });

  let container: HTMLDivElement;
  let view: EditorView | null = $state.raw(null);

  $effect(() => {
    const editorView = new EditorView({
      parent: container,
      doc: '',
      extensions: [
        // Tab accepts the selected completion, or else indents. Escape and then Tab moves the focus out of the editor.
        Prec.high(keymap.of([{ key: 'Tab', run: acceptCompletion }, indentWithTab])),
        basicSetup,
        python(),
        createCodeTheme(),
        ...extensions,
        ...(readOnly ? [EditorState.readOnly.of(true), EditorView.editable.of(false), EditorView.lineWrapping] : []),
        highlightedLineField,
        EditorView.contentAttributes.of({ 'aria-label': label }),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            onCodeChange(update.state.doc.toString());
          }
        }),
      ],
    });
    view = editorView;
    return () => {
      editorView.destroy();
      view = null;
    };
  });

  /** Puts the cursor at the start of a line (1 is the first line), scrolls the line into view, and focuses the editor. */
  export function revealLine(line: number): void {
    if (view === null) {
      return;
    }
    const lineNumber = Math.min(Math.max(1, Math.trunc(line)), view.state.doc.lines);
    const position = view.state.doc.line(lineNumber).from;
    view.dispatch({ selection: { anchor: position }, effects: EditorView.scrollIntoView(position, { y: 'center' }) });
    view.focus();
  }

  /** Scrolls `region` (a scrolling parent of the editor) so that the line is a third down from its top. */
  export function scrollLineIntoRegion(line: number, region: HTMLElement): void {
    if (view === null) {
      return;
    }
    const currentView = view;
    currentView.requestMeasure({
      read: () => {
        const lineNumber = Math.min(Math.max(1, Math.trunc(line)), currentView.state.doc.lines);
        const block = currentView.lineBlockAt(currentView.state.doc.line(lineNumber).from);
        const lineTopInRegion = currentView.documentTop + block.top - region.getBoundingClientRect().top;
        return region.scrollTop + lineTopInRegion - region.clientHeight / LINE_POSITION_PARTS;
      },
      write: (scrollTop) => {
        region.scrollTop = Math.max(0, scrollTop);
      },
    });
  }

  // The page sets new code when the user opens another version. The editor keeps its cursor when the code is the same.
  $effect(() => {
    const currentView = view;
    if (currentView === null) {
      return;
    }
    const currentCode = currentView.state.doc.toString();
    if (currentCode !== code) {
      currentView.dispatch({ changes: { from: 0, to: currentCode.length, insert: code } });
    }
  });

  // The code effect above runs first, so the line numbers are lines of the new code.
  $effect(() => {
    const currentView = view;
    const lines = highlightedLines;
    if (currentView !== null) {
      currentView.dispatch({ effects: setHighlightedLines.of(lines) });
    }
  });
</script>

<div class="code-editor" bind:this={container}></div>

<style>
  .code-editor {
    height: 100%;
    min-height: 0;
    border: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
  }

  .code-editor :global(.code-editor__highlighted-line) {
    background: var(--cds-layer-selected-01);
  }

  .code-editor :global(.cm-editor) {
    height: 100%;
  }

  /* The editor owns its scroll region. The scrollbar is styled, so Safari also shows it (docs/architecture.md section 13.1). */
  .code-editor :global(.cm-scroller) {
    overflow: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--cds-icon-secondary) var(--cds-layer-accent-01);
  }

  .code-editor :global(.cm-scroller::-webkit-scrollbar) {
    width: var(--cds-spacing-03);
    height: var(--cds-spacing-03);
  }

  .code-editor :global(.cm-scroller::-webkit-scrollbar-track) {
    background: var(--cds-layer-accent-01);
  }

  .code-editor :global(.cm-scroller::-webkit-scrollbar-thumb) {
    background: var(--cds-icon-secondary);
  }
</style>
