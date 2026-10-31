<!-- The condition card of the assistant side column (docs/architecture/assistant.md 25.12.4): the name and the market
     of the screen, its full condition bar with the change marks against the definition before, and the buttons "Open
     screen", "Discard", and "Keep". After a click, the buttons become the state "Kept" or "Discarded"; a discarded card
     fades. The indicator names come from the indicator catalog, as on the screen page. -->
<script module lang="ts">
  import { listScreenIndicators, type ScreenIndicator } from '#lib/screen';

  // One catalog read for all cards of the page.
  let catalogRead: Promise<ScreenIndicator[]> | null = null;

  function readCatalog(): Promise<ScreenIndicator[]> {
    catalogRead ??= listScreenIndicators(fetch).then((result) => {
      if (result.kind === 'ok') {
        return result.value;
      }
      catalogRead = null;
      return [];
    });
    return catalogRead;
  }
</script>

<script lang="ts">
  import { resolve } from '$app/paths';
  import type { ScreenItem } from '#lib/assistant';
  import { Button, StatusIndicator } from '#lib/foundation/carbon';
  import { ConditionBar, nameDefinitionIndicators, type ScreenDefinition } from '#lib/screen';
  import type { DiffChoice } from './assistant_session.svelte';

  interface Props {
    item: ScreenItem;
    choice: DiffChoice | undefined;
    onKeep: (screenId: number) => void;
    onDiscard: (screenId: number) => void;
  }

  const { item, choice, onKeep, onDiscard }: Props = $props();

  let catalog = $state<ScreenIndicator[] | null>(null);

  $effect(() => {
    void readCatalog().then((value) => {
      catalog = value;
    });
  });

  const definition = $derived(item.definition as ScreenDefinition);
  const previous = $derived(item.previousDefinition as ScreenDefinition | null);
  const href = $derived(resolve('/screens/[[screenId]]', { screenId: String(item.screenId) }));
</script>

<article class={['cds--tile assistant-card screen-card', choice === 'discarded' && 'screen-card--discarded']} aria-label={`Screen ${item.name}`}>
  <div class="screen-card__head">
    <span class="screen-card__name">{item.name}</span>
    <span class="screen-card__market">{item.market}</span>
  </div>
  {#if catalog !== null}
    <div class="screen-card__conditions">
      <ConditionBar
        {definition}
        indicatorNames={nameDefinitionIndicators(definition, catalog)}
        counts={item.counts}
        compareWith={previous === null ? null : { definition: previous, indicatorNames: nameDefinitionIndicators(previous, catalog) }}
      />
    </div>
  {/if}
  <div class="screen-card__buttons">
    {#if choice === 'discarded'}
      <StatusIndicator label="Discarded" kind="neutral" />
    {:else}
      {#if choice === 'kept'}
        <StatusIndicator label="Kept" kind="success" />
      {/if}
      <a class="cds--btn cds--btn--ghost cds--btn--sm" {href}>Open screen</a>
      {#if choice === undefined}
        <Button
          kind="secondary"
          size="sm"
          onclick={() => {
            onDiscard(item.screenId);
          }}>Discard</Button
        >
        <Button
          kind="primary"
          size="sm"
          onclick={() => {
            onKeep(item.screenId);
          }}>Keep</Button
        >
      {/if}
    {/if}
  </div>
</article>

<style>
  .assistant-card {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: var(--cds-spacing-03);
    min-inline-size: 0;
    padding: var(--cds-spacing-04);
  }

  .screen-card__head {
    display: flex;
    align-items: baseline;
    gap: var(--cds-spacing-03);
    min-inline-size: 0;
  }

  .screen-card__name {
    flex: 1;
    min-inline-size: 0;
    overflow: hidden;
    font-size: var(--cds-heading-compact-01-font-size);
    font-weight: var(--cds-heading-compact-01-font-weight);
    line-height: var(--cds-heading-compact-01-line-height);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .screen-card__market {
    color: var(--cds-text-secondary);
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
  }

  /* The bar wraps, and a long tag wraps its text, so each condition stays visible in the narrow column. */
  .screen-card__conditions :global(.condition-tag) {
    block-size: auto;
    max-inline-size: 100%;
  }

  .screen-card__conditions :global(.condition-tag .cds--tag__label) {
    flex-wrap: wrap;
    white-space: normal;
  }

  .screen-card--discarded .screen-card__conditions {
    opacity: 0.55;
  }

  .screen-card__buttons {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--cds-spacing-03);
  }
</style>
