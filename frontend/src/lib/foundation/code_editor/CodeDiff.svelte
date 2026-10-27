<!-- Read-only side-by-side diff of two Python texts: @codemirror/merge. It has no domain meaning (docs/architecture.md
     section 13). Long unchanged parts are collapsed. The diff owns its scroll region with a styled scrollbar. -->
<script lang="ts">
  import { MergeView } from '@codemirror/merge';
  import { python } from '@codemirror/lang-python';
  import { EditorState, type EditorStateConfig } from '@codemirror/state';
  import { EditorView, basicSetup } from 'codemirror';

  interface Props {
    firstCode: string;
    secondCode: string;
    firstLabel: string;
    secondLabel: string;
  }

  const { firstCode, secondCode, firstLabel, secondLabel }: Props = $props();

  let container: HTMLDivElement;

  function makeSide(code: string, label: string): EditorStateConfig {
    return {
      doc: code,
      extensions: [
        basicSetup,
        python(),
        EditorState.readOnly.of(true),
        EditorView.editable.of(false),
        EditorView.contentAttributes.of({ 'aria-label': label }),
      ],
    };
  }

  $effect(() => {
    const mergeView = new MergeView({
      parent: container,
      a: makeSide(firstCode, firstLabel),
      b: makeSide(secondCode, secondLabel),
      collapseUnchanged: { margin: 3, minSize: 4 },
    });
    return () => {
      mergeView.destroy();
    };
  });
</script>

<div class="code-diff">
  <div class="diff-labels" aria-hidden="true">
    <span>{firstLabel}</span>
    <span>{secondLabel}</span>
  </div>
  <div class="diff-view" bind:this={container}></div>
</div>

<style>
  .code-diff {
    border: 1px solid var(--color-border);
    background: var(--color-surface);
  }

  .diff-labels {
    display: grid;
    grid-template-columns: 1fr 1fr;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.875rem;
    font-weight: 600;
  }

  .diff-labels span {
    padding: 0.375rem 0.75rem;
  }

  /* The merge view scrolls inside itself. The scrollbar is styled, so Safari also shows it (section 13.1). */
  .diff-view :global(.cm-mergeView) {
    max-height: 28rem;
    overflow: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--color-muted) transparent;
  }

  .diff-view :global(.cm-mergeView::-webkit-scrollbar) {
    width: 10px;
    height: 10px;
  }

  .diff-view :global(.cm-mergeView::-webkit-scrollbar-thumb) {
    border-radius: 5px;
    background: var(--color-muted);
  }

  .diff-view :global(.cm-editor) {
    font-size: 0.8125rem;
  }
</style>
