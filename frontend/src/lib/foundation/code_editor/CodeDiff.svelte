<!-- Read-only side-by-side diff of two Python texts: @codemirror/merge. It has no domain meaning (docs/architecture.md
     section 13). Long unchanged parts are collapsed and long lines wrap. The diff scrolls inside a ScrollRegion, which
     draws its own track in all browsers (section 13.1). With `fill`, it fills its parent (a workbench panel). -->
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
    /** Fill the height of the parent (a workbench panel) and scroll in it, instead of a maximum height. */
    fill?: boolean;
  }

  const { firstCode, secondCode, firstLabel, secondLabel, collapseUnchanged = true, fill = false }: Props = $props();

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

<div class={['code-diff', fill && 'code-diff--fill']}>
  <div class="diff-labels" aria-hidden="true">
    <span>{firstLabel}</span>
    <span>{secondLabel}</span>
  </div>
  <div class="diff-body">
    <ScrollRegion label="Code difference" maxHeight="min(32rem, 60vh)" {fill}>
      <div class="diff-view" bind:this={container}></div>
    </ScrollRegion>
  </div>
</div>

<style>
  .code-diff {
    border: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
  }

  .code-diff--fill {
    display: flex;
    flex-direction: column;
    block-size: 100%;
    border: 0;
  }

  .code-diff--fill .diff-body {
    flex: 1;
    min-block-size: 0;
  }

  .diff-labels {
    display: grid;
    grid-template-columns: 1fr 1fr;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    font-size: var(--cds-heading-compact-01-font-size);
    font-weight: var(--cds-heading-compact-01-font-weight);
    line-height: var(--cds-heading-compact-01-line-height);
    letter-spacing: var(--cds-heading-compact-01-letter-spacing);
  }

  .diff-labels span {
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  /* The ScrollRegion scrolls the merge view, so the merge view does not scroll itself. */
  .diff-view :global(.cm-mergeView) {
    overflow: visible;
  }
</style>
