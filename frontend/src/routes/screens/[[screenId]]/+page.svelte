<!-- Screen page (docs/architecture/screen.md section 24.10): a workbench. URL: /screens/<id>?result=<screen result id>;
     /screens opens the screen that the user opened last (browser storage), or the first screen of the list. Without
     ?result, the page shows the last run. Start side: the "Screens" side column (ScreenList) with "New screen". Main
     region: the title row (the name, the US / HK switch, "Save as new screen", and "Save screen" for unsaved changes), the condition
     bar with its edit popover, the table toolbar (Result N / Excluded N, the daily bars date, the run time, "Add to
     watchlist", and "Run backtest on this screen result"; batch actions when rows are selected), and the result or the
     excluded table. Each change of a condition runs the changed screen at once (section 24.13). An HK screen shows the
     survivorship bias warning. The backtest buttons open the "New backtest" form with the screen, the screen result,
     and the selected rows (screen.md section 24.9). -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { navigating, page } from '$app/state';
  import { ContentSwitcher, IconButton, InlineNotification, Popover } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { SideColumn, Workbench } from '#lib/foundation/workbench';
  import { SurvivorshipBiasWarning } from '#lib/market_data';
  import {
    addCondition,
    ConditionBar,
    ConditionEditor,
    createScreen,
    groupProblems,
    isDraftChanged,
    listScreenIndicators,
    listScreens,
    nameDefinitionIndicators,
    newCondition,
    newScreen,
    readScreen,
    readScreenResult,
    readTarget,
    removeCondition,
    runScreenDraft,
    saveScreen,
    ScreenExclusionTable,
    ScreenResultTable,
    switchMarket,
    writeTarget,
    type ConditionKind,
    type ConditionTarget,
    type Screen,
    type ScreenIndicator,
    type ScreenListItem,
    type ScreenMarket,
    type ScreenProblem,
    type ScreenResult,
  } from '#lib/screen';
  import type { Backtest, ScreenSource } from '#lib/backtest';
  import { addToWatchlist } from '#lib/watchlist';
  import StartBacktestDialog from '../../backtests/StartBacktestDialog.svelte';
  import { readLastScreenId, writeLastScreenId } from '../last_screen';
  import ScreenList from '../ScreenList.svelte';

  type ShownTable = 'result' | 'excluded';
  type Definition = Record<string, unknown>;
  type Draft = { market: ScreenMarket; definition: Definition };
  type ListTarget = ConditionTarget & { part: 'filters' | 'indicator_conditions' };

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
  let draft = $state<(Draft & { screenId: number }) | null>(null);
  // The save that runs now. The other save button stays disabled until it ends.
  let saving = $state<'save' | 'new' | null>(null);
  // Counts the draft runs. Only the answer of the last run changes the page.
  let runNumber = 0;
  // The screen result of the last draft run. The page shows it also while the URL changes to its ?result.
  let runResultId: number | null = null;
  // The problems of the last 422 answer of a run or a save (section 24.6), by tag, for one screen.
  let problems = $state<{ screenId: number; action: 'run' | 'save'; byTarget: Map<string, string[]>; other: string[] } | null>(
    null,
  );
  let catalog: ScreenIndicator[] = $state([]);
  // The edit popover of one tag, or of a new condition of "Add condition" (target null).
  let editing = $state<{ target: ConditionTarget | null; item: Definition; anchor: HTMLElement | null } | null>(null);
  let backtestSource = $state<ScreenSource | null>(null);
  let isCreating = $state(false);
  // The reason of the last failed "New screen".
  let createMessage = $state('');

  const shownScreen = $derived(screen !== null && screen.id === screenId ? screen : null);
  const screenResultId = $derived.by(() => {
    if (routeResultId !== null) {
      return Number(routeResultId);
    }
    return shownScreen?.recent_screen_results[0]?.id ?? null;
  });
  const shownResult = $derived(
    screenResult !== null && (screenResult.id === screenResultId || screenResult.id === runResultId) && screenResult.screen_id === screenId
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

  $effect(() => {
    void listScreenIndicators(fetch).then((result) => {
      if (result.kind === 'ok') {
        catalog = result.value;
      }
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
    // The page has the screen result of its own run already.
    if (id === runResultId && screenResult?.id === id) {
      return;
    }
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
  const shownProblems = $derived(problems !== null && problems.screenId === screenId ? problems : null);
  // An HK draft of a US screen runs HK instruments, so the warning follows the market of the draft.
  const shownMarket = $derived(shownDraft?.market ?? shownScreen?.market ?? null);
  const isChanged = $derived(
    shownScreen !== null &&
      shownDraft !== null &&
      isDraftChanged({ market: shownScreen.market, definition: shownScreen.definition }, shownDraft),
  );

  // Each change runs the draft at once. The run makes a screen result; the saved screen stays the same.
  async function changeDraft(current: Screen, market: ScreenMarket, definition: Definition): Promise<void> {
    draft = { screenId: current.id, market, definition };
    resultMessage = '';
    problems = null;
    runNumber += 1;
    const thisRun = runNumber;
    const result = await runScreenDraft(fetch, current.id, { market, definition });
    // The answer of a run that a newer change replaced is stale.
    if (thisRun !== runNumber) {
      return;
    }
    if (result.kind === 'check_failed') {
      problems = { screenId: current.id, action: 'run', ...groupProblems(result.problems) };
      return;
    }
    if (result.kind === 'failed') {
      resultMessage = result.message;
      return;
    }
    runResultId = result.value.id;
    selectedPositions = [];
    screenResult = result.value;
    const path = `${resolve('/screens/[[screenId]]', { screenId: String(current.id) })}?result=${String(result.value.id)}`;
    // eslint-disable-next-line svelte/no-navigation-without-resolve -- the path above is resolved.
    await goto(path, { replaceState: true });
  }

  function currentDraft(result: ScreenResult): Draft {
    return shownDraft ?? { market: result.market, definition: result.definition };
  }

  function removeFromDraft(current: Screen, result: ScreenResult, target: ListTarget): void {
    const base = currentDraft(result);
    void changeDraft(current, base.market, removeCondition(base.definition, target) as Definition);
  }

  function switchDraftMarket(current: Screen, result: ScreenResult, market: ScreenMarket): void {
    const base = currentDraft(result);
    void changeDraft(current, market, switchMarket(base.definition, market) as Definition);
  }

  function applyEdit(current: Screen, result: ScreenResult, item: Definition): void {
    if (editing === null) {
      return;
    }
    const base = currentDraft(result);
    const changed =
      editing.target === null ? addCondition(base.definition, item) : writeTarget(base.definition, editing.target, item);
    editing = null;
    void changeDraft(current, base.market, changed as Definition);
  }

  function removeEdited(current: Screen, result: ScreenResult): void {
    const target = editing?.target;
    editing = null;
    if (target?.part === 'filters' || target?.part === 'indicator_conditions') {
      removeFromDraft(current, result, target);
    }
  }

  // The bar shows the draft. Its funnel counts and names come from the screen result of the same definition.
  function barOf(result: ScreenResult): {
    definition: Definition;
    names: ScreenResult['indicator_names'];
    counts: ScreenResult['summary'] | null;
  } {
    const base = currentDraft(result);
    return !isDraftChanged({ market: result.market, definition: result.definition }, base)
      ? { definition: result.definition, names: result.indicator_names, counts: result.summary }
      : { definition: base.definition, names: nameDefinitionIndicators(base.definition, catalog), counts: null };
  }

  function showSaveFailure(
    current: Screen,
    failure: { kind: 'failed'; message: string } | { kind: 'check_failed'; problems: ScreenProblem[] },
  ): void {
    if (failure.kind === 'check_failed') {
      problems = { screenId: current.id, action: 'save', ...groupProblems(failure.problems) };
    } else {
      resultMessage = failure.message;
    }
  }

  async function saveDraft(current: Screen): Promise<void> {
    if (shownDraft === null) {
      return;
    }
    saving = 'save';
    const saved = await saveScreen(fetch, current, shownDraft.definition);
    saving = null;
    if (saved.kind !== 'ok') {
      showSaveFailure(current, saved);
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
    const base = currentDraft(result);
    // The page goes to the new screen: the answer of a draft run of this screen is stale.
    runNumber += 1;
    saving = 'new';
    const created = await createScreen(fetch, {
      name: newScreenName(current.name),
      market: base.market,
      definition: base.definition,
    });
    saving = null;
    if (created.kind !== 'ok') {
      showSaveFailure(current, created);
      return;
    }
    const listed = await listScreens(fetch);
    if (listed.kind === 'ok') {
      screens = listed.value;
    }
    draft = null;
    problems = null;
    const run = await runScreenDraft(fetch, created.value.id, base);
    const target = resolve('/screens/[[screenId]]', { screenId: String(created.value.id) });
    // eslint-disable-next-line svelte/no-navigation-without-resolve -- the target is resolved.
    await goto(run.kind === 'ok' ? `${target}?result=${String(run.value.id)}` : target);
  }

  // "New screen": creates the default screen (section 24.13), runs it, and opens its screen result.
  async function createNewScreen(): Promise<void> {
    const body = newScreen(screens.map((item) => item.name));
    isCreating = true;
    createMessage = '';
    const created = await createScreen(fetch, body);
    if (created.kind !== 'ok') {
      isCreating = false;
      createMessage = created.kind === 'failed' ? created.message : created.problems.map((problem) => problem.message).join(' ');
      return;
    }
    const listed = await listScreens(fetch);
    if (listed.kind === 'ok') {
      screens = listed.value;
    }
    const run = await runScreenDraft(fetch, created.value.id, { market: body.market, definition: body.definition });
    isCreating = false;
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

  function openBacktestForm(result: ScreenResult, positions: number[] | null): void {
    backtestSource = {
      screenId: result.screen_id,
      screenResultId: result.id,
      symbols:
        positions === null
          ? null
          : result.rows.filter((row) => positions.includes(row.position)).map((row) => row.symbol),
    };
  }

  function openStartedBacktest(backtest: Backtest): void {
    void goto(resolve('/backtests/[[backtestId]]', { backtestId: String(backtest.id) }));
  }
</script>

<Workbench>
  <SideColumn label="Screens" side="start" width="20rem" storageKey="atrade.screen-page.list-column">
    {#snippet actions()}
      <IconButton
        label={isCreating ? 'Creating screen…' : 'New screen'}
        icon={Add16}
        disabled={isCreating}
        busy={isCreating}
        onclick={() => void createNewScreen()}
      />
    {/snippet}
    <ScreenList
      {screens}
      errorMessage={listMessage}
      {createMessage}
      onCreateMessageClose={() => {
        createMessage = '';
      }}
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
          <div class="market-switch">
            <ContentSwitcher
              label="Market"
              size="sm"
              items={[
                { value: 'US', label: 'US' },
                { value: 'HK', label: 'HK' },
              ]}
              value={currentDraft(result).market}
              onValueChange={(value: ScreenMarket) => {
                switchDraftMarket(current, result, value);
              }}
            />
          </div>
          <div class="title-actions">
            <button
              type="button"
              class="cds--btn cds--btn--tertiary cds--btn--sm cds--layout--size-sm"
              disabled={saving !== null}
              onclick={() => void saveAsNewScreen(current, result)}>{saving === 'new' ? 'Saving screen…' : 'Save as new screen'}</button
            >
            {#if isChanged && shownDraft?.market === current.market}
              <button
                type="button"
                class="cds--btn cds--btn--primary cds--btn--sm cds--layout--size-sm"
                disabled={saving !== null}
                onclick={() => void saveDraft(current)}>{saving === 'save' ? 'Saving screen…' : 'Save screen'}</button
              >
            {/if}
          </div>
        {/if}
      </div>
      {#if shownMarket === 'HK'}
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
        {@const bar = barOf(result)}
        <div class="condition-region">
          <ScrollRegion label="Condition bar" maxHeight="7.5rem">
            <ConditionBar
              definition={bar.definition}
              indicatorNames={bar.names}
              counts={bar.counts}
              problems={shownProblems?.byTarget}
              onRemove={(target: ListTarget) => {
                removeFromDraft(current, result, target);
              }}
              onEdit={(target: ConditionTarget, anchor: HTMLElement) => {
                editing = { target, item: readTarget(currentDraft(result).definition, target), anchor };
              }}
              onAdd={(kind: ConditionKind, anchor: HTMLElement | null) => {
                editing = { target: null, item: newCondition(kind, currentDraft(result).market), anchor };
              }}
            />
          </ScrollRegion>
        </div>
        {#if shownProblems !== null && shownProblems.other.length > 0}
          <InlineNotification kind="error" title={shownProblems.action === 'run' ? 'Screen not run' : 'Screen not saved'} subtitle={shownProblems.other.join(' ')} lowContrast />
        {/if}
        <Popover
          open={editing !== null}
          onOpenChange={(open: boolean) => {
            if (!open) {
              editing = null;
            }
          }}
          anchor={editing?.anchor ?? null}
          label="Edit condition"
        >
          {#if editing !== null}
            {@const edit = editing}
            {#key edit}
              <ConditionEditor
                initial={edit.item}
                market={currentDraft(result).market}
                {catalog}
                isNew={edit.target === null}
                canRemove={edit.target?.part === 'filters' || edit.target?.part === 'indicator_conditions'}
                onApply={(item: Definition) => {
                  applyEdit(current, result, item);
                }}
                onRemove={() => {
                  removeEdited(current, result);
                }}
                onCancel={() => {
                  editing = null;
                }}
              />
            {/key}
          {/if}
        </Popover>
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
                  class="cds--btn cds--btn--primary cds--btn--sm"
                  onclick={() => {
                    openBacktestForm(result, selectedPositions);
                  }}>Run backtest on selected</button
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
                class="cds--btn cds--btn--ghost cds--btn--sm toolbar-button"
                disabled={isAdding || result.rows.length === 0}
                onclick={() => void addRowsToWatchlist(result, null)}
                >{isAdding ? 'Adding to watchlist…' : 'Add to watchlist'}</button
              >
              <button
                type="button"
                class="cds--btn cds--btn--primary cds--btn--sm"
                onclick={() => {
                  openBacktestForm(result, null);
                }}>Run backtest on this screen result</button
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

<StartBacktestDialog
  open={backtestSource !== null}
  onOpenChange={(open: boolean) => {
    if (!open) {
      backtestSource = null;
    }
  }}
  onStarted={openStartedBacktest}
  screenSource={backtestSource}
/>

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

  .title-row {
    display: flex;
    flex: none;
    gap: var(--cds-spacing-05);
    align-items: center;
  }

  /* The US / HK switch: 2 short labels. */
  .market-switch {
    flex: none;
    inline-size: var(--cds-spacing-13);
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
