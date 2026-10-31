<!-- A GFM table with the Carbon data table structure. A number column is right aligned with tabular numbers. A wide
     table scrolls in its own styled track (docs/architecture.md section 13.1). -->
<script lang="ts">
  import MarkdownInline from './MarkdownInline.svelte';
  import type { MarkdownInline as Inline, TableColumn } from './markdown_blocks';

  interface Props {
    columns: readonly TableColumn[];
    header: readonly Inline[][];
    rows: readonly Inline[][][];
  }

  const { columns, header, rows }: Props = $props();
</script>

<div class="cds--data-table-container markdown-table">
  <div class="cds--data-table-content markdown-table__scroll">
    <table class="cds--data-table cds--data-table--xs">
      <thead>
        <tr>
          {#each header as cell, index (index)}
            <th scope="col" align={columns[index]?.align}
              ><div class="cds--table-header-label"><MarkdownInline inlines={cell} /></div></th
            >
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each rows as row, rowIndex (rowIndex)}
          <tr>
            {#each row as cell, index (index)}
              <td align={columns[index]?.align} class={[columns[index]?.isNumber === true && 'markdown-table__number']}
                ><MarkdownInline inlines={cell} /></td
              >
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>

<style>
  .markdown-table {
    min-inline-size: 0;
    padding-block-start: 0;
  }

  .markdown-table__scroll {
    overflow-x: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--cds-icon-secondary) var(--cds-layer-accent-01);
  }

  .markdown-table__scroll::-webkit-scrollbar {
    height: var(--cds-spacing-03);
  }

  .markdown-table__scroll::-webkit-scrollbar-track {
    background: var(--cds-layer-accent-01);
  }

  .markdown-table__scroll::-webkit-scrollbar-thumb {
    background: var(--cds-icon-secondary);
  }

  .markdown-table th[align='right'] .cds--table-header-label {
    text-align: end;
  }

  .markdown-table th[align='center'] .cds--table-header-label {
    text-align: center;
  }

  .markdown-table__number {
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
</style>
