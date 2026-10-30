<!-- The "New strategy" dialog (docs/architecture/strategy.md section 9.7.1): the strategy name, the list of start points
     on the left, and the selected start point on the right. "Create strategy" sends the name and the start point. -->
<script lang="ts">
  import { Dialog, InlineNotification, TextInput } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { createStrategy, listStrategyTemplates, type StartPoint, type StrategyDetail, type StrategyTemplate } from '#lib/strategy';

  interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCreated: (strategy: StrategyDetail) => void;
  }

  const { open, onOpenChange, onCreated }: Props = $props();

  // The backend refuses a longer name.
  const STRATEGY_NAME_MAX_LENGTH = 100;
  const BLANK_START_POINTS: { id: StartPoint; name: string }[] = [
    { id: 'blank_code', name: 'Blank code' },
    { id: 'blank_rules', name: 'Blank rules' },
  ];

  let name = $state('');
  let startFrom = $state<StartPoint>('blank_code');
  let templates: StrategyTemplate[] = $state([]);
  let templateMessage = $state('');
  let createMessage = $state('');
  let isCreating = $state(false);
  let form: HTMLFormElement | undefined = $state();
  let list: HTMLUListElement | undefined = $state();

  const startPointIds = $derived<StartPoint[]>([
    ...BLANK_START_POINTS.map((point) => point.id),
    ...templates.map((template) => template.id as StartPoint),
  ]);
  const selectedTemplate = $derived(templates.find((template) => template.id === startFrom) ?? null);
  const selectedName = $derived(
    selectedTemplate?.name ?? BLANK_START_POINTS.find((point) => point.id === startFrom)?.name ?? '',
  );

  $effect(() => {
    if (!open) {
      return;
    }
    name = '';
    startFrom = 'blank_code';
    createMessage = '';
    templateMessage = '';
    void listStrategyTemplates(fetch).then((result) => {
      if (result.kind === 'failed') {
        templateMessage = result.message;
        return;
      }
      templates = result.value;
    });
  });

  // The arrow keys move the selection, as in a radio group. The selected option is the one tab stop of the list.
  function moveSelection(event: KeyboardEvent): void {
    const step = event.key === 'ArrowDown' ? 1 : event.key === 'ArrowUp' ? -1 : 0;
    if (step === 0) {
      return;
    }
    event.preventDefault();
    const index = startPointIds.indexOf(startFrom);
    const next = startPointIds[Math.min(Math.max(index + step, 0), startPointIds.length - 1)];
    if (next === undefined) {
      return;
    }
    startFrom = next;
    list?.querySelector<HTMLElement>(`[data-start-point="${next}"]`)?.focus();
  }

  async function submit(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    isCreating = true;
    const result = await createStrategy(fetch, name, startFrom);
    isCreating = false;
    if (result.kind === 'failed') {
      createMessage = result.message;
      return;
    }
    onCreated(result.strategy);
  }
</script>

{#snippet option(id: StartPoint, optionName: string)}
  <li
    class="cds--contained-list-item cds--contained-list-item--clickable start-point"
    role="option"
    aria-selected={startFrom === id}
    tabindex={startFrom === id ? 0 : -1}
    data-start-point={id}
    onclick={() => {
      startFrom = id;
    }}
    onkeydown={(event: KeyboardEvent) => {
      if (event.key === ' ' || event.key === 'Enter') {
        event.preventDefault();
        startFrom = id;
      }
    }}
  >
    <div class="cds--contained-list-item__content">{optionName}</div>
  </li>
{/snippet}

<Dialog
  {open}
  {onOpenChange}
  title="New strategy"
  size="lg"
  primaryText={isCreating ? 'Creating…' : 'Create strategy'}
  busy={isCreating}
  onPrimary={() => form?.requestSubmit()}
>
  <form class="new-strategy-form" aria-label="New strategy" bind:this={form} onsubmit={submit}>
    <TextInput label="Strategy name" name="name" bind:value={name} required maxlength={STRATEGY_NAME_MAX_LENGTH} />
    <div class="start-points">
      <div class="start-point-list">
        <ScrollRegion label="Start points" fill>
          <ul
            class="cds--contained-list__list"
            role="listbox"
            aria-label="Start from"
            bind:this={list}
            onkeydown={moveSelection}
          >
            {#each BLANK_START_POINTS as point (point.id)}
              {@render option(point.id, point.name)}
            {/each}
            {#if templates.length > 0}
              <li class="cds--contained-list__header" role="presentation">
                <span class="cds--contained-list__label">Templates</span>
              </li>
              {#each templates as template (template.id)}
                {@render option(template.id as StartPoint, template.name)}
              {/each}
            {/if}
          </ul>
        </ScrollRegion>
      </div>
      <div class="start-point-detail">
        <ScrollRegion label={selectedName} fill>
          <div class="detail">
            <h3>{selectedName}</h3>
            {#if selectedTemplate !== null}
              <dl class="template-rows">
                <dt>Entry</dt>
                <dd>{selectedTemplate.entry}</dd>
                <dt>Exit</dt>
                <dd>{selectedTemplate.exit}</dd>
                <dt>Defaults</dt>
                <dd class="numbers">{selectedTemplate.defaults}</dd>
                <dt>Market</dt>
                <dd>{selectedTemplate.market}</dd>
                <dt>Bar period</dt>
                <dd>{selectedTemplate.bar_period}</dd>
                <dt>Evidence</dt>
                <dd>{selectedTemplate.evidence}</dd>
                <dt>Sources</dt>
                <dd class="sources">
                  {#each selectedTemplate.sources as source (source.url)}
                    <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- an external DOI link, not an app path. -->
                    <a class="cds--link" href={source.url} target="_blank" rel="noopener noreferrer">{source.label}</a>
                  {/each}
                </dd>
                <dt>Differs from source</dt>
                <dd>{selectedTemplate.differs_from_source}</dd>
              </dl>
            {/if}
          </div>
        </ScrollRegion>
      </div>
    </div>
  </form>
  {#if templateMessage !== ''}
    <InlineNotification kind="error" lowContrast title="Templates not loaded" subtitle={templateMessage} />
  {/if}
  {#if createMessage !== ''}
    <InlineNotification kind="error" lowContrast title="Strategy not created" subtitle={createMessage} />
  {/if}
</Dialog>

<style>
  .new-strategy-form {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-06);
    margin-block-end: var(--cds-spacing-05);
  }

  .start-points {
    display: grid;
    grid-template-columns: calc(var(--cds-spacing-13) + var(--cds-spacing-10)) minmax(0, 1fr);
    block-size: calc(var(--cds-spacing-13) * 2);
    background: var(--cds-layer-01);
  }

  .start-point-list,
  .start-point-detail {
    display: flex;
    flex-direction: column;
    min-block-size: 0;
  }

  .start-point-list {
    border-inline-end: 1px solid var(--cds-border-subtle-01);
  }

  .start-point {
    cursor: pointer;
  }

  .start-point[aria-selected='true'] {
    background: var(--cds-layer-selected-01);
  }

  .start-point:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .detail {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-05);
    padding: var(--cds-spacing-05);
  }

  .detail h3 {
    margin: 0;
    font-size: var(--cds-heading-compact-02-font-size);
    font-weight: var(--cds-heading-compact-02-font-weight);
    line-height: var(--cds-heading-compact-02-line-height);
    letter-spacing: var(--cds-heading-compact-02-letter-spacing);
  }

  .template-rows {
    display: grid;
    grid-template-columns: var(--cds-spacing-12) minmax(0, 1fr);
    gap: var(--cds-spacing-03) var(--cds-spacing-05);
    margin: 0;
  }

  .template-rows dt {
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .template-rows dd {
    margin: 0;
  }

  .numbers {
    font-variant-numeric: tabular-nums;
  }

  .sources {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-02);
  }
</style>
