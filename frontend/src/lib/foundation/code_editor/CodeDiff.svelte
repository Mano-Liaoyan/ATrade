<!-- Read-only side-by-side diff of two Python texts: @codemirror/merge. It has no domain meaning (docs/architecture.md
     section 13). Long unchanged parts are collapsed and long lines wrap. The diff scrolls inside a ScrollRegion, which
     draws its own track in all browsers (section 13.1). -->
<script lang="ts">
  import { MergeView } from '@codemirror/merge';
  import { python } from '@codemirror/lang-python';
  import { EditorState, type EditorStateConfig } from '@codemirror/state';
  import { EditorView, basicSetup } from 'codemirror';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { createCodeTheme } from './code_theme';

  interface Props {
    firstCode: string;
    secondCode: string;
    firstLabel: string;
    secondLabel: string;
    /** Collapse long unchanged parts. Turn it off to show all code, for example when both sides are the same. */
    collapseUnchanged?: boolean;
  }

  const { firstCode, secondCode, firstLabel, secondLabel, collapseUnchanged = true }: Props = $props();

  let container: HTMLDivElement;

  function makeSide(code: string, label: string): EditorStateConfig {
    return {
      doc: code,
      extensions: [
        basicSetup,
        python(),
        createCodeTheme(),
        EditorView.lineWrapping,
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
      ...(collapseUnchanged ? { collapseUnchanged: { margin: 3, minSize: 4 } } : {}),
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
  <ScrollRegion label="Code difference" maxHeight="min(32rem, 60vh)">
    <div class="diff-view" bind:this={container}></div>
  </ScrollRegion>
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

  /* The ScrollRegion scrolls the merge view, so the merge view does not scroll itself. */
  .diff-view :global(.cm-mergeView) {
    overflow: visible;
  }

  .diff-view :global(.cm-editor) {
    font-size: 0.8125rem;
  }
</style>
