<!-- The 32px header line of a workbench panel or side column: the content (a name, a price line) on the left and the
     `end` content (for example the panel buttons) at the right end. All header lines of all pages have this height and
     this bottom border. A Panel with tabs gives its Carbon tab line the same class (atrade-panel-header). -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    children: Snippet;
    end?: Snippet;
  }

  const { children, end }: Props = $props();
</script>

<div class="atrade-panel-header">
  <div class="atrade-panel-header__content">{@render children()}</div>
  {#if end !== undefined}
    <div class="atrade-panel-header__end">{@render end()}</div>
  {/if}
</div>

<style>
  :global(.atrade-panel-header) {
    display: flex;
    flex: none;
    align-items: center;
    box-sizing: border-box;
    block-size: var(--cds-spacing-07);
    min-inline-size: 0;
    box-shadow: inset 0 -1px 0 var(--cds-border-subtle-01);
  }

  .atrade-panel-header__content {
    display: flex;
    flex: 1;
    align-items: center;
    gap: var(--cds-spacing-05);
    min-inline-size: 0;
    block-size: 100%;
    padding-inline-start: var(--cds-spacing-05);
  }

  :global(.atrade-panel-header__end) {
    display: flex;
    flex: none;
    align-items: center;
  }

  /* The name of a panel or a side column. A heading is a name only. */
  .atrade-panel-header__content :global(:is(h1, h2, h3)) {
    margin: 0;
    overflow: hidden;
    font-size: var(--cds-heading-compact-01-font-size);
    font-weight: var(--cds-heading-compact-01-font-weight);
    line-height: var(--cds-heading-compact-01-line-height);
    letter-spacing: var(--cds-heading-compact-01-letter-spacing);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* A Carbon tab line in a header line: the tabs fill the line, and the line keeps its own bottom border. */
  :global(.atrade-panel-header > .cds--tabs) {
    flex: 1;
    min-inline-size: 0;
    block-size: 100%;
    min-block-size: 0;
  }
</style>
