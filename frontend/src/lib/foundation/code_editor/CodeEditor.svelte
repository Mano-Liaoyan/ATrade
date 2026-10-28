<!-- Python code editor: CodeMirror 6 with @codemirror/lang-python. It has no domain meaning (docs/architecture.md section 13).
     `revealLine(line)` (through `bind:this`) puts the cursor at the start of a line, scrolls it into view, and focuses
     the editor, for example from a list of code problems. -->
<script lang="ts">
  import { acceptCompletion } from '@codemirror/autocomplete';
  import { indentWithTab } from '@codemirror/commands';
  import { python } from '@codemirror/lang-python';
  import { Prec, type Extension } from '@codemirror/state';
  import { keymap } from '@codemirror/view';
  import { EditorView, basicSetup } from 'codemirror';
  import { createCodeTheme } from './code_theme';

  interface Props {
    code: string;
    label: string;
    onCodeChange: (code: string) => void;
    /** More CodeMirror extensions, for example a language server client. The editor reads them once. */
    extensions?: Extension[];
  }

  const { code, label, onCodeChange, extensions = [] }: Props = $props();

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
</script>

<div class="code-editor" bind:this={container}></div>

<style>
  .code-editor {
    height: 100%;
    min-height: 0;
    border: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
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
