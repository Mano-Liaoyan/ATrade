<!-- Screen page (docs/architecture/screen.md section 24.10): a workbench. URL: /screens/<id>?result=<screen result id>;
     /screens opens the screen that the user opened last (browser storage), or the first screen of the list. Without
     ?result, the page shows the last run. Start side: the "Screens" side column (ScreenList). Main region: the title
     row (the name), the read-only condition bar, the table toolbar (Result N / Excluded N, the daily bars date, the
     run time, and "Add to watchlist"; batch actions when rows are selected), and the result or the excluded table. An
     HK screen shows the survivorship bias warning. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { navigating, page } from '$app/state';
  import { ContentSwitcher, Dialog, InlineNotification, Select, TextInput } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { SideColumn, Workbench } from '#lib/foundation/workbench';
  import { SurvivorshipBiasWarning } from '#lib/market_data';
  import {
    addIndicatorCondition,
    changeComparison,
    ConditionBar,
    createScreen,
    isDraftChanged,
    listScreens,
    removeCondition,
    runScreenDraft,
    saveScreen,
    switchMarket,
    readScreen,
    readScreenResult,
    ScreenExclusionTable,
    ScreenResultTable,
    type RemovableGroup,
    type Screen,
    type ScreenListItem,
    type ScreenMarket,
    type ScreenResult,
  } from '#lib/screen';
  import { addToWatchlist } from '#lib/watchlist';
  import { readLastScreenId, writeLastScreenId } from '../last_screen';
  import ScreenList from '../ScreenList.svelte';

  type ShownTable = 'result' | 'excluded';

  const routeScreenId = $derived(page.params['screenId']);
  // A route segment that is not a whole number opens no screen.
  const screenId = $derived(routeScreenId !== undefined && /^\d+$/.test(routeScreenId) ? Number(routeScreenId) : null);
  const routeResultId = $derived(page.url.searchParams.get('result'));

  let screens: ScreenListItem[] = $state([]);
  let isListRead = $state(false);
  let listMessage = $state('');
  let screen = $state<Screen | null>(null);
  let screenMessage = $state('');
  let screenResult = $state<ScreenResult | null>(null);
  let resultMessage = $state('');
  let shownTable: ShownTable = $state('result');
  let selectedPositions: number[] = $state([]);
  let isAdding = $state(false);
  let addMessage = $state<{ kind: 'success' | 'error'; text: string } | null>(null);
  // The changed, unsaved screen (section 24.13). Null when the page shows the saved screen.
  let draft = $state<{ screenId: number; market: ScreenMarket; definition: Record<string, unknown> } | null>(null);
  let isSaving = $state(false);
  // The edit dialog of one comparison: a Close or Avg trading value filter, or a compare condition.
  let editing = $state<{ group: RemovableGroup; index: number; operator: string; value: string } | null>(null);
  const OPERATOR_ITEMS = [
    { value: '<', label: '<' },
    { value: '<=', label: '≤' },
    { value: '>', label: '>' },
    { value: '>=', label: '≥' },
  ];

  const shownScreen = $derived(screen !== null && screen.id === screenId ? screen : null);
  const screenResultId = $derived.by(() => {
    if (routeResultId !== null) {
      return Number(routeResultId);
    }
    return shownScreen?.recent_screen_results[0]?.id ?? null;
  });
  const shownResult = $derived(
    screenResult !== null && screenResult.id === screenResultId && screenResult.screen_id === screenId
      ? screenResult
      : null,
  );

  $effect(() => {
    void listScreens(fetch).then((result) => {
      isListRead = true;
      if (result.kind === 'failed') {
        listMessage = result.message;
        return;
      }
      listMessage = '';
      screens = result.value;
    });
  });

  // /screens opens the screen that the user opened last, or the first screen of the list.
  $effect(() => {
    if (navigating.to !== null || screenId !== null || screens.length === 0) {
      return;
    }
    const lastId = readLastScreenId();
    const target = screens.find((item) => item.id === lastId) ?? screens[0];
    if (target !== undefined) {
      void goto(resolve('/screens/[[screenId]]', { screenId: String(target.id) }), { replace: true });
    }
  });

  $effect(() => {
    if (screenId === null) {
      return;
    }
    const id = screenId;
    writeLastScreenId(id);
    screenMessage = '';
    void readScreen(fetch, id).then((result) => {
      // A reply for a screen that is not open any more is stale.
      if (id !== screenId) {
        return;
      }
      if (result.kind === 'failed') {
        screenMessage = result.message;
        return;
      }
      screenMessage = '';
      screen = result.value;
    });
  });

  $effect(() => {
    if (screenResultId === null) {
      return;
    }
    const id = screenResultId;
    selectedPositions = [];
    addMessage = null;
    resultMessage = '';
    void readScreenResult(fetch, id).then((result) => {
      if (id !== screenResultId) {
        return;
      }
      if (result.kind === 'failed') {
        resultMessage = result.message;
        return;
      }
      resultMessage = '';
      screenResult = result.value;
    });
  });

  const shownDraft = $derived(draft !== null && draft.screenId === screenId ? draft : null);
  const isChanged = $derived(
    shownScreen !== null &&
      shownDraft !== null &&
      isDraftChanged({ market: shownScreen.market, definition: shownScreen.definition }, shownDraft),
  );

  // Each change runs the draft at once. The run makes a screen result; the saved screen stays the same.
  async function changeDraft(current: Screen, market: ScreenMarket, definition: Record<string, unknown>): Promise<void> {
    draft = { screenId: current.id, market, definition };
    resultMessage = '';
    const result = await runScreenDraft(fetch, current.id, { market, definition });
    if (draft.definition !== definition || draft.market !== market) {
      return;
    }
    if (result.kind === 'failed') {
      resultMessage = result.message;
      return;
    }
    screenResult = result.value;
    const path = `${resolve('/screens/[[screenId]]', { screenId: String(current.id) })}?result=${String(result.value.id)}`;
    // eslint-disable-next-line svelte/no-navigation-without-resolve -- the path above is resolved.
    await goto(path, { replaceState: true });
  }

  function currentDraft(current: Screen, result: ScreenResult): { market: ScreenMarket; definition: Record<string, unknown> } {
    return shownDraft ?? { market: result.market, definition: result.definition };
  }

  function removeFromDraft(current: Screen, result: ScreenResult, group: RemovableGroup, index: number): void {
    const base = currentDraft(current, result);
    void changeDraft(current, base.market, removeCondition(base.definition, group, index) as Record<string, unknown>);
  }

  function switchDraftMarket(current: Screen, result: ScreenResult, market: ScreenMarket): void {
    const base = currentDraft(current, result);
    void changeDraft(current, market, switchMarket(base.definition, market) as Record<string, unknown>);
  }

  function addToDraft(current: Screen, result: ScreenResult): void {
    const base = currentDraft(current, result);
    void changeDraft(current, base.market, addIndicatorCondition(base.definition) as Record<string, unknown>);
  }

  function openEdit(current: Screen, result: ScreenResult, group: RemovableGroup, index: number): void {
    const key = group === 'Filters' ? 'filters' : 'indicator_conditions';
    const list = currentDraft(current, result).definition[key];
    const item = (Array.isArray(list) ? list[index] : undefined) as Record<string, unknown> | undefined;
    if (item === undefined || typeof item['operator'] !== 'string') {
      return;
    }
    editing = { group, index, operator: item['operator'], value: typeof item['value'] === 'string' ? item['value'] : '' };
  }

  function applyEdit(current: Screen, result: ScreenResult): void {
    if (editing === null) {
      return;
    }
    const base = currentDraft(current, result);
    const changed = changeComparison(base.definition, editing.group, editing.index, editing.operator, editing.value);
    editing = null;
    void changeDraft(current, base.market, changed as Record<string, unknown>);
  }

  async function saveDraft(current: Screen): Promise<void> {
    if (shownDraft === null) {
      return;
    }
    isSaving = true;
    const saved = await saveScreen(fetch, current, shownDraft.definition);
    isSaving = false;
    if (saved.kind === 'failed') {
      resultMessage = saved.message;
      return;
    }
    screen = saved.value;
    draft = null;
  }

  function newScreenName(name: string): string {
    const names = new Set(screens.map((item) => item.name));
    let candidate = `${name} copy`;
    for (let number = 2; names.has(candidate); number += 1) {
      candidate = `${name} copy ${String(number)}`;
    }
    return candidate;
  }

  async function saveAsNewScreen(current: Screen, result: ScreenResult): Promise<void> {
    const base = currentDraft(current, result);
    isSaving = true;
    const created = await createScreen(fetch, {
      name: newScreenName(current.name),
      market: base.market,
      definition: base.definition,
    });
    isSaving = false;
    if (created.kind === 'failed') {
      resultMessage = created.message;
      return;
    }
    const listed = await listScreens(fetch);
    if (listed.kind === 'ok') {
      screens = listed.value;
    }
    draft = null;
    const run = await runScreenDraft(fetch, created.value.id, base);
    const target = resolve('/screens/[[screenId]]', { screenId: String(created.value.id) });
    // eslint-disable-next-line svelte/no-navigation-without-resolve -- the target is resolved.
    await goto(run.kind === 'ok' ? `${target}?result=${String(run.value.id)}` : target);
  }

  // The watchlist add route checks each instrument with IBKR, so the page adds the instruments one after the other.
  async function addRowsToWatchlist(result: ScreenResult, positions: number[] | null): Promise<void> {
    const rows = positions === null ? result.rows : result.rows.filter((row) => positions.includes(row.position));
    isAdding = true;
    addMessage = null;
    let addedCount = 0;
    let lastFailure = '';
    for (const row of rows) {
      const added = await addToWatchlist(fetch, row);
      if (added.kind === 'ok') {
        addedCount += 1;
      } else {
        lastFailure = added.message;
      }
    }
    isAdding = false;
    selectedPositions = [];
    addMessage =
      addedCount === rows.length
        ? { kind: 'success', text: `Added ${String(addedCount)} instruments to the watchlist` }
        : {
            kind: 'error',
            text: `Added ${String(addedCount)} of ${String(rows.length)} instruments to the watchlist. ${lastFailure}`,
          };
  }
</script>

<Workbench>
  <SideColumn label="Screens" side="start" width="20rem" storageKey="atrade.screen-page.list-column">
    <ScreenList
      {screens}
      errorMessage={listMessage}
      openScreen={shownScreen}
      openScreenResultId={shownResult?.id ?? null}
    />
  </SideColumn>

  <main class="screen-main">
    {#if shownScreen === null}
      {#if screenMessage !== ''}
        <InlineNotification kind="error" title="Screen not read" subtitle={screenMessage} lowContrast />
      {:else if isListRead && screens.length === 0 && listMessage === ''}
        <EmptyText text="No screens" />
      {/if}
    {:else}
      {@const current = shownScreen}
      <div class="title-row">
        <h1 class="screen-title">{current.name}</h1>
        {#if shownResult !== null}
          {@const result = shownResult}
          <ContentSwitcher
            label="Market"
            size="sm"
            items={[
              { value: 'US', label: 'US' },
              { value: 'HK', label: 'HK' },
            ]}
            value={currentDraft(current, result).market}
            onValueChange={(value: ScreenMarket) => {
              switchDraftMarket(current, result, value);
            }}
          />
          <div class="title-actions">
            <button
              type="button"
              class="cds--btn cds--btn--tertiary cds--btn--sm"
              disabled={isSaving}
              onclick={() => void saveAsNewScreen(current, result)}>Save as new screen</button
            >
            {#if isChanged && shownDraft?.market === current.market}
              <button
                type="button"
                class="cds--btn cds--btn--primary cds--btn--sm"
                disabled={isSaving}
                onclick={() => void saveDraft(current)}>Save screen</button
              >
            {/if}
          </div>
        {/if}
      </div>
      {#if current.market === 'HK'}
        <SurvivorshipBiasWarning />
      {/if}
      {#if resultMessage !== ''}
        <InlineNotification kind="error" title="Screen result not read" subtitle={resultMessage} lowContrast />
      {:else if shownResult === null}
        {#if current.recent_screen_results.length === 0}
          <EmptyText text="No runs" />
        {/if}
      {:else}
        {@const result = shownResult}
        <div class="condition-region">
          <ScrollRegion label="Condition bar" maxHeight="7.5rem">
            <ConditionBar
              definition={result.definition}
              indicatorNames={result.indicator_names}
              counts={result.summary}
              onRemove={(group: RemovableGroup, index: number) => {
                removeFromDraft(current, result, group, index);
              }}
              onEdit={(group: RemovableGroup, index: number) => {
                openEdit(current, result, group, index);
              }}
              onAdd={() => {
                addToDraft(current, result);
              }}
            />
          </ScrollRegion>
        </div>
        {#if editing !== null}
          {@const edit = editing}
          <Dialog
            open
            onOpenChange={(open: boolean) => {
              if (!open) {
                editing = null;
              }
            }}
            title="Edit condition"
            size="xs"
            primaryText="Apply condition"
            secondaryText="Cancel"
            onPrimary={() => {
              applyEdit(current, result);
            }}
          >
            <Select
              label="Operator"
              items={OPERATOR_ITEMS}
              value={edit.operator}
              onValueChange={(value: string) => {
                edit.operator = value;
              }}
            />
            <TextInput
              label="Value"
              class="number-input"
              inputmode="decimal"
              value={edit.value}
              oninput={(event: Event) => {
                edit.value = (event.currentTarget as HTMLInputElement).value;
              }}
            />
          </Dialog>
        {/if}
        {#if addMessage !== null}
          <InlineNotification
            kind={addMessage.kind}
            title={addMessage.text}
            lowContrast
            onClose={() => {
              addMessage = null;
            }}
          />
        {/if}
        <section class="cds--table-toolbar cds--table-toolbar--sm table-toolbar" aria-label="Screen result toolbar">
          {#if selectedPositions.length > 0}
            <div class="cds--batch-actions cds--batch-actions--active">
              <div class="cds--batch-summary">
                <p class="cds--batch-summary__para" role="status">{selectedPositions.length} selected</p>
              </div>
              <div class="cds--action-list">
                <button
                  type="button"
                  class="cds--btn cds--btn--primary cds--btn--sm"
                  disabled={isAdding}
                  onclick={() => void addRowsToWatchlist(result, selectedPositions)}
                  >{isAdding ? 'Adding to watchlist…' : 'Add to watchlist'}</button
                >
                <button
                  type="button"
                  class="cds--btn cds--btn--primary cds--btn--sm cds--batch-summary__cancel"
                  onclick={() => {
                    selectedPositions = [];
                  }}>Cancel</button
                >
              </div>
            </div>
          {:else}
            <div class="toolbar-content">
              <ContentSwitcher
                label="Screen result table"
                size="sm"
                items={[
                  { value: 'result', label: `Result ${String(result.summary.result_count)}` },
                  { value: 'excluded', label: `Excluded ${String(result.exclusions.length)}` },
                ]}
                value={shownTable}
                onValueChange={(value: ShownTable) => {
                  shownTable = value;
                }}
              />
              <span class="run-info"
                >Daily bars {result.summary.daily_bars_date ?? '–'} · {formatUtcTime(result.summary.run_at_utc)}</span
              >
              <button
                type="button"
                class="cds--btn cds--btn--primary cds--btn--sm toolbar-button"
                disabled={isAdding || result.rows.length === 0}
                onclick={() => void addRowsToWatchlist(result, null)}
                >{isAdding ? 'Adding to watchlist…' : 'Add to watchlist'}</button
              >
            </div>
          {/if}
        </section>
        <div class="table-region">
          {#if shownTable === 'result'}
            <ScreenResultTable
              rows={result.rows}
              definition={result.definition}
              indicatorNames={result.indicator_names}
              {selectedPositions}
              onSelectionChange={(positions: number[]) => {
                selectedPositions = positions;
              }}
            />
          {:else}
            <ScreenExclusionTable exclusions={result.exclusions} />
          {/if}
        </div>
      {/if}
    {/if}
  </main>
</Workbench>

<style>
  .screen-main {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: var(--cds-spacing-03);
    min-block-size: 0;
    min-inline-size: 0;
    padding: var(--cds-spacing-05);
    /* $layer-01, so the $background group strips of the condition bar show (screen.md section 24.10.1). */
    background: var(--cds-layer-01);
  }

  /* The value of the edit dialog: a number, right-aligned with tabular numbers. */
  :global(.number-input) {
    text-align: end;
    font-variant-numeric: tabular-nums;
  }

  .title-row {
    display: flex;
    flex: none;
    gap: var(--cds-spacing-05);
    align-items: center;
  }

  .title-actions {
    display: flex;
    gap: var(--cds-spacing-03);
    margin-inline-start: auto;
  }

  .screen-title {
    flex: none;
    margin: 0;
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
  }

  /* 2 or 3 lines of conditions; more lines scroll in the bar. */
  .condition-region {
    flex: none;
  }

  .table-toolbar {
    flex: none;
    position: relative;
  }

  .toolbar-content {
    display: flex;
    flex: 1;
    gap: var(--cds-spacing-05);
    align-items: center;
  }

  .run-info {
    color: var(--cds-text-secondary);
    font-size: var(--cds-body-compact-01-font-size);
    font-variant-numeric: tabular-nums;
  }

  .toolbar-button {
    margin-inline-start: auto;
  }

  .table-region {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-block-size: 0;
  }
</style>
