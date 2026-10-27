<!-- Python code editor: CodeMirror 6 with @codemirror/lang-python. It has no domain meaning (docs/architecture.md section 13). -->
<script lang="ts">
  import { python } from '@codemirror/lang-python';
  import { EditorView, basicSetup } from 'codemirror';

  interface Props {
    code: string;
    label: string;
    onCodeChange: (code: string) => void;
  }

  const { code, label, onCodeChange }: Props = $props();

  let container: HTMLDivElement;
  let view: EditorView | null = $state.raw(null);

  $effect(() => {
    const editorView = new EditorView({
      parent: container,
      doc: '',
      extensions: [
        basicSetup,
        python(),
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
    border: 1px solid var(--color-border);
    background: var(--color-surface);
  }

  .code-editor :global(.cm-editor) {
    height: 100%;
  }

  /* The editor owns its scroll region. The scrollbar is styled, so Safari also shows it (docs/architecture.md section 13.1). */
  .code-editor :global(.cm-scroller) {
    overflow: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--color-muted) transparent;
  }

  .code-editor :global(.cm-scroller::-webkit-scrollbar) {
    width: 10px;
    height: 10px;
  }

  .code-editor :global(.cm-scroller::-webkit-scrollbar-thumb) {
    border-radius: 5px;
    background: var(--color-muted);
  }
</style>
