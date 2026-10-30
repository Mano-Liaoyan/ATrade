<!-- The "Source order" section of the settings page (docs/architecture/market_data.md section 8.7.3): a Carbon
     structured list with one row for each bar source, in the source order. A move saves the new order at once. -->
<script lang="ts">
  import ArrowDown16 from '@carbon/icons/es/arrow--down/16.js';
  import ArrowUp16 from '@carbon/icons/es/arrow--up/16.js';
  import { IconButton, InlineNotification } from '#lib/foundation/carbon';
  import {
    formatBarSource,
    moveBarSource,
    readSourceOrder,
    saveSourceOrder,
    type BarSource,
    type MoveDirection,
  } from './source_order';

  const headingId = $props.id();
  let sourceOrder: BarSource[] = $state([]);
  let errorMessage: string | null = $state(null);

  $effect(() => {
    void readSourceOrder(fetch).then((readResult) => {
      if (readResult.kind === 'ok') {
        sourceOrder = readResult.value;
      } else {
        errorMessage = readResult.message;
      }
    });
  });

  async function move(index: number, direction: MoveDirection): Promise<void> {
    const saveResult = await saveSourceOrder(fetch, moveBarSource(sourceOrder, index, direction));
    if (saveResult.kind === 'ok') {
      sourceOrder = saveResult.value;
      errorMessage = null;
    } else {
      errorMessage = saveResult.message;
    }
  }
</script>

<section class="source-order" aria-labelledby={headingId}>
  <h2 id={headingId} class="source-order__heading">Source order</h2>
  {#if errorMessage !== null}
    <InlineNotification kind="error" title={errorMessage} lowContrast />
  {/if}
  <div class="cds--structured-list cds--structured-list--condensed" role="table" aria-labelledby={headingId}>
    <div class="cds--structured-list-tbody" role="rowgroup">
      {#each sourceOrder as barSource, index (barSource)}
        {@const name = formatBarSource(barSource)}
        <div class="cds--structured-list-row" role="row">
          <div class="cds--structured-list-td source-order__name" role="cell">{name}</div>
          <div class="cds--structured-list-td source-order__moves" role="cell">
            {#if index > 0}
              <IconButton label={`Move ${name} up`} icon={ArrowUp16} onclick={() => void move(index, 'up')} />
            {/if}
            {#if index < sourceOrder.length - 1}
              <IconButton label={`Move ${name} down`} icon={ArrowDown16} onclick={() => void move(index, 'down')} />
            {/if}
          </div>
        </div>
      {/each}
    </div>
  </div>
</section>

<style>
  .source-order {
    max-inline-size: 32rem;
  }

  .source-order__heading {
    margin-block-end: var(--cds-spacing-05);
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
    letter-spacing: var(--cds-heading-03-letter-spacing);
  }

  .source-order__name {
    vertical-align: middle;
  }

  /* The move buttons stay at the end of the row, in the same place in each row. */
  .source-order__moves {
    inline-size: calc(2 * var(--cds-spacing-07));
    text-align: end;
    white-space: nowrap;
  }
</style>
