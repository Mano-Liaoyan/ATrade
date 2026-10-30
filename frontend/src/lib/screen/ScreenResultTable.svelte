<!-- The result table of a screen result (docs/architecture/screen.md section 24.10.2): a Carbon sortable data table
     with a selection column. A click on a column header sorts by it; a second click changes the direction. Number
     columns are right-aligned with tabular numbers. -->
<script lang="ts">
  import ArrowDown16 from '@carbon/icons/es/arrow--down/16.js';
  import ArrowUp16 from '@carbon/icons/es/arrow--up/16.js';
  import { Checkbox, Icon } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { MISSING_VALUE } from '#lib/foundation/value_format';
  import type { IndicatorNames, ScreenDefinition } from './condition_bar';
  import {
    listResultColumns,
    sortResultRows,
    type ResultColumn,
    type ScreenResultRow,
    type SortDirection,
  } from './result_table';

  interface Props {
    rows: ScreenResultRow[];
    definition: ScreenDefinition;
    indicatorNames: IndicatorNames;
    /** The positions of the selected rows. */
    selectedPositions: number[];
    onSelectionChange: (positions: number[]) => void;
  }

  const { rows, definition, indicatorNames, selectedPositions, onSelectionChange }: Props = $props();

  const NUMBER_FORMAT = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });
  const columns = $derived(listResultColumns(definition, indicatorNames));
  let sortKey = $state('position');
  let sortDirection: SortDirection = $state('ascending');
  const sortColumn = $derived(columns.find((column) => column.key === sortKey) ?? columns[0]);
  const sortedRows = $derived(sortColumn === undefined ? rows : sortResultRows(rows, sortColumn, sortDirection));
  const isAllSelected = $derived(rows.length > 0 && selectedPositions.length === rows.length);

  function sortBy(column: ResultColumn): void {
    if (column.key === sortKey) {
      sortDirection = sortDirection === 'ascending' ? 'descending' : 'ascending';
      return;
    }
    sortKey = column.key;
    sortDirection = 'ascending';
  }

  function formatCell(column: ResultColumn, row: ScreenResultRow): string {
    if (column.key === 'close') {
      return row.last_price;
    }
    const value = column.read(row);
    if (value === null) {
      return MISSING_VALUE;
    }
    return typeof value === 'number' && column.key !== 'position' ? NUMBER_FORMAT.format(value) : String(value);
  }

  function toggleRow(position: number, isChecked: boolean): void {
    onSelectionChange(
      isChecked ? [...selectedPositions, position] : selectedPositions.filter((selected) => selected !== position),
    );
  }
</script>

<ScrollRegion label="Result table" fill>
  <div class="cds--data-table-container table">
    <div class="cds--data-table-content">
      <table class="cds--data-table cds--data-table--sm cds--data-table--sort">
        <thead>
          <tr>
            <th scope="col" class="cds--table-column-checkbox">
              <Checkbox
                label="Select all rows"
                hideLabel
                checked={isAllSelected}
                onCheckedChange={(isChecked: boolean) => {
                  onSelectionChange(isChecked ? rows.map((row) => row.position) : []);
                }}
              />
            </th>
            {#each columns as column (column.key)}
              {@const isSorted = column.key === sortKey}
              <th
                scope="col"
                align={column.isNumber ? 'right' : undefined}
                aria-sort={isSorted ? sortDirection : 'none'}
              >
                <button
                  type="button"
                  class={[
                    'cds--table-sort',
                    isSorted && 'cds--table-sort--active',
                    isSorted && sortDirection === 'descending' && 'cds--table-sort--descending',
                  ]}
                  onclick={() => {
                    sortBy(column);
                  }}
                >
                  <span class="cds--table-sort__flex">
                    <div class="cds--table-header-label">{column.header}</div>
                    <Icon
                      icon={isSorted && sortDirection === 'descending' ? ArrowDown16 : ArrowUp16}
                      class="cds--table-sort__icon"
                    />
                  </span>
                </button>
              </th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each sortedRows as row (row.position)}
            <tr class={[selectedPositions.includes(row.position) && 'cds--data-table--selected']}>
              <td class="cds--table-column-checkbox">
                <Checkbox
                  label={`Select ${row.symbol}`}
                  hideLabel
                  checked={selectedPositions.includes(row.position)}
                  onCheckedChange={(isChecked: boolean) => {
                    toggleRow(row.position, isChecked);
                  }}
                />
              </td>
              {#each columns as column (column.key)}
                <td align={column.isNumber ? 'right' : undefined}>{formatCell(column, row)}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
</ScrollRegion>

<style>
  .table :global(thead th) {
    position: sticky;
    inset-block-start: 0;
    z-index: 1;
  }

  .table :global(td[align='right']) {
    font-variant-numeric: tabular-nums;
  }

  .table :global(th[align='right'] .cds--table-sort__flex) {
    justify-content: flex-end;
  }
</style>
