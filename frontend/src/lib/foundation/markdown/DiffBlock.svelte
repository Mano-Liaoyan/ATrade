<!-- A diff block of a markdown text. A closed block with a unified diff (file headers and hunks) shows in the diff view
     of @pierre/diffs, loaded on demand, with the + and - markers ("classic" indicators) and the Carbon code colors.
     The Copy icon button sits at the end of the file header line of the diff view. An open block, or a diff that the
     diff view cannot read, shows in the plain diff view of CodeBlock. -->
<script lang="ts">
  import { mount, unmount } from 'svelte';
  import CodeBlock from './CodeBlock.svelte';
  import CopyButton from './CopyButton.svelte';
  import { loadDiffView, type DiffView } from './diff_view';

  interface Props {
    language: string;
    text: string;
    closed: boolean;
  }

  const { language, text, closed }: Props = $props();

  let container: HTMLDivElement | undefined = $state();
  let shown = $state(false);

  $effect(() => {
    const source = text;
    const element = container;
    if (!closed || element === undefined) {
      return;
    }
    let view: DiffView | undefined;
    let current = true;
    const copyTarget = document.createElement('div');
    const copyButton = mount(CopyButton, { target: copyTarget, props: { text: source } });
    loadDiffView().then(
      (createView) => {
        if (!current) {
          return;
        }
        view = createView(element, source, copyTarget);
        shown = view !== undefined;
      },
      () => {
        shown = false;
      },
    );
    return () => {
      current = false;
      view?.destroy();
      void unmount(copyButton);
      shown = false;
    };
  });
</script>

{#if closed}
  <figure
    class={['markdown-diff', !shown && 'markdown-diff--hidden']}
    aria-label={language === '' ? 'diff' : language}
    aria-hidden={!shown}
  >
    <div class="markdown-diff__view" bind:this={container}></div>
  </figure>
{/if}
{#if !shown}
  <CodeBlock language={language === '' ? 'diff' : language} {text} {closed} display="diff" />
{/if}

<style>
  .markdown-diff {
    position: relative;
    min-inline-size: 0;
    margin: 0;
    background-color: var(--cds-layer-01);
    box-shadow: inset 0 0 0 1px var(--cds-border-subtle-01);
  }

  /* The diff view renders in the hidden figure; the plain diff view shows until it is ready. */
  .markdown-diff--hidden {
    block-size: 0;
    overflow: hidden;
    visibility: hidden;
  }

  /* The diff view reads these variables in its shadow root. Carbon tokens only. */
  .markdown-diff__view {
    --diffs-font-family: var(--cds-code-01-font-family, 'IBM Plex Mono', monospace);
    --diffs-header-font-family: var(--cds-body-compact-01-font-family, 'IBM Plex Sans', sans-serif);
    --diffs-font-size: var(--cds-code-01-font-size);
    --diffs-line-height: var(--cds-code-01-line-height);
    --diffs-font-features: 'tnum';
    --diffs-background: var(--cds-layer-01);
    --diffs-bg-context-override: var(--cds-layer-01);
    --diffs-bg-context-gutter-override: var(--cds-layer-01);
    --diffs-bg-separator-override: var(--cds-layer-accent-01);
    --diffs-bg-buffer-override: var(--cds-layer-01);
    --diffs-bg-hover-override: var(--cds-layer-hover-01);
    --diffs-fg-number-override: var(--cds-text-secondary);
    --diffs-addition-color-override: var(--cds-support-success);
    --diffs-deletion-color-override: var(--cds-support-error);
    --diffs-bg-addition-override: color-mix(in srgb, var(--cds-support-success) 15%, transparent);
    --diffs-bg-addition-number-override: color-mix(in srgb, var(--cds-support-success) 15%, transparent);
    --diffs-bg-addition-emphasis-override: color-mix(in srgb, var(--cds-support-success) 40%, transparent);
    --diffs-bg-deletion-override: color-mix(in srgb, var(--cds-support-error) 15%, transparent);
    --diffs-bg-deletion-number-override: color-mix(in srgb, var(--cds-support-error) 15%, transparent);
    --diffs-bg-deletion-emphasis-override: color-mix(in srgb, var(--cds-support-error) 40%, transparent);

    min-inline-size: 0;
  }
</style>
