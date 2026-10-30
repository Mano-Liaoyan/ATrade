<!-- The excluded table of a screen result (docs/architecture/screen.md section 24.10.2): each excluded instrument and
     its reason, the condition or "No value: <indicator>". -->
<script lang="ts">
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { describeExclusionReason } from './result_table';
  import type { ScreenResultExclusion } from './screen_api';

  const { exclusions }: { exclusions: ScreenResultExclusion[] } = $props();

  const COLUMNS: TableColumn[] = [{ header: 'Symbol' }, { header: 'Exchange' }, { header: 'Reason' }];
</script>

<ScrollRegion label="Excluded table" fill>
  <div class="table">
    <DataTable columns={COLUMNS} size="sm">
      {#snippet rows()}
        {#each exclusions as exclusion (`${exclusion.symbol}/${exclusion.exchange}/${exclusion.currency}`)}
          <tr>
            <th scope="row">{exclusion.symbol}</th>
            <td>{exclusion.exchange}</td>
            <td>{describeExclusionReason(exclusion.reason)}</td>
          </tr>
        {/each}
      {/snippet}
    </DataTable>
  </div>
</ScrollRegion>

<style>
  .table :global(thead th) {
    position: sticky;
    inset-block-start: 0;
    z-index: 1;
  }
</style>
