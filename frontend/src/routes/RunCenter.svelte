<!-- The center area of a run page (backtests, parameter sweeps, forward tests). A failed read of RunWorkbench shows above
     the content, so the rows and the numbers of the last read stay and carry the reason. -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { InlineNotification } from '#lib/foundation/carbon';

  interface Props {
    workbench: { listMessage: string; detailMessage: string };
    listTitle: string;
    detailTitle: string;
    children: Snippet;
  }

  const { workbench, listTitle, detailTitle, children }: Props = $props();
</script>

<div class="run-center">
  {#if workbench.listMessage !== ''}
    <InlineNotification kind="error" title={listTitle} subtitle={workbench.listMessage} lowContrast />
  {/if}
  {#if workbench.detailMessage !== ''}
    <InlineNotification kind="error" title={detailTitle} subtitle={workbench.detailMessage} lowContrast />
  {/if}
  {@render children()}
</div>

<style>
  .run-center {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-block-size: 0;
    min-inline-size: 0;
  }
</style>
