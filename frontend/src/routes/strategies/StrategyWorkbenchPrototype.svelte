<!-- PROTOTYPE (#99), throwaway: the strategy workbench (QuantConnect IDE layout). Left: the strategy list. Main: a
     toolbar of icon buttons, then the results pane and the editor pane with a splitter between them. The swap button
     puts the editor on top or at the bottom; the browser keeps the choice. -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import ArrowDown16 from '@carbon/icons/es/arrow--down/16.js';
  import ArrowUp16 from '@carbon/icons/es/arrow--up/16.js';
  import InProgress16 from '@carbon/icons/es/in-progress/16.js';
  import PlayFilledAlt16 from '@carbon/icons/es/play--filled--alt/16.js';
  import Radio16 from '@carbon/icons/es/radio/16.js';
  import Save16 from '@carbon/icons/es/save/16.js';
  import StopFilledAlt16 from '@carbon/icons/es/stop--filled--alt/16.js';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { isFinalStatus, listBacktests, type Backtest } from '#lib/backtest';
  import { Dialog, InlineNotification, Select, TextInput } from '#lib/foundation/carbon';
  import { buildSocketUrl, openLiveSocket } from '#lib/foundation/live_socket';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import {
    FORWARD_TESTS_SOCKET_PATH,
    readForwardTestsMessage,
    stopForwardTest,
    type ForwardTest,
  } from '#lib/forward_test';
  import {
    clearDraft,
    connectStrategyLanguageServer,
    createStrategy,
    formatVersionLabel,
    listStrategies,
    readDraft,
    readStrategy,
    readStrategyVersion,
    saveStrategyVersion,
    writeDraft,
    type CodeProblem,
    type StrategyDetail,
    type StrategyListItem,
    type StrategyVersion,
  } from '#lib/strategy';
  import WorkbenchBacktestDialog from './WorkbenchBacktestDialog.svelte';
  import WorkbenchEditorPane from './WorkbenchEditorPane.svelte';
  import WorkbenchForwardTestDialog from './WorkbenchForwardTestDialog.svelte';
  import WorkbenchIconButton from './WorkbenchIconButton.svelte';
  import WorkbenchOutputPanel from './WorkbenchOutputPanel.svelte';
  import WorkbenchResultsPane from './WorkbenchResultsPane.svelte';
  import {
    backtestTab,
    clampTopFraction,
    DEFAULT_TOP_FRACTION,
    findMaximizedPanel,
    isPanelCollapsed,
    openOutputPanel,
    readPaneOrder,
    readPanelSizes,
    restoreMaximized,
    toggleMaximized,
    toggleMinimized,
    writePanelSizes,
    writePaneOrder,
    type OutputTab,
    type PaneOrder,
    type PanelId,
    type PanelSizes,
    type ResultsTab,
  } from './workbench_layout';

  const { strategyId }: { strategyId: number | null } = $props();

  const BACKTEST_POLL_MILLISECONDS = 2000;
  const SPLITTER_KEY_STEP = 0.05;
  const STRATEGY_NAME_MAX_LENGTH = 100;
  const PERCENT = 100;
  // The tab of the newest backtest. The results pane maps it to the real backtest tab.
  const NEWEST_BACKTEST_TAB = backtestTab(0);

  let strategies: StrategyListItem[] = $state([]);
  let listError = $state('');
  let strategy = $state<StrategyDetail | null>(null);
  let openVersion = $state<StrategyVersion | null>(null);
  let editorCode = $state('');
  let problems: CodeProblem[] = $state([]);
  let outputLines: string[] = $state([]);
  let isSaving = $state(false);
  let allBacktests: Backtest[] = $state([]);
  let forwardTests: ForwardTest[] = $state([]);
  let resultsTab = $state<ResultsTab>(NEWEST_BACKTEST_TAB);
  let resultsBacktestId = $state<number | null>(null);
  let paneOrder = $state<PaneOrder>(readPaneOrder(() => localStorage));
  let topFraction = $state(DEFAULT_TOP_FRACTION);
  let panelSizes = $state<PanelSizes>(readPanelSizes(() => localStorage));
  let outputTab = $state<OutputTab>('problems');
  let paneStack: HTMLDivElement | undefined = $state();
  let isDraggingSplitter = $state(false);
  let isBacktestDialogOpen = $state(false);
  let isForwardTestDialogOpen = $state(false);
  let isNewStrategyDialogOpen = $state(false);
  let newStrategyName = $state('');
  let createError = $state('');
  let isCreating = $state(false);

  const activeStrategyId = $derived(strategyId ?? strategies[0]?.id ?? null);
  const strategyBacktests = $derived(
    allBacktests.filter((backtest) => backtest.strategy_id === activeStrategyId).sort((first, second) => second.id - first.id),
  );
  const runningBacktest = $derived(strategyBacktests.find((backtest) => !isFinalStatus(backtest.status)) ?? null);
  const hasRunningBacktest = $derived(allBacktests.some((backtest) => !isFinalStatus(backtest.status)));
  const runningForwardTest = $derived(
    forwardTests.find(
      (forwardTest) => forwardTest.strategy_id === activeStrategyId && forwardTest.desired_state === 'running',
    ) ?? null,
  );
  const shownBacktestId = $derived(
    strategyBacktests.some((backtest) => backtest.id === resultsBacktestId)
      ? resultsBacktestId
      : (strategyBacktests[0]?.id ?? null),
  );
  const shownTab = $derived<ResultsTab>(
    resultsTab.startsWith('backtest-') && shownBacktestId !== null && !strategyBacktests.some((backtest) => backtestTab(backtest.id) === resultsTab)
      ? backtestTab(shownBacktestId)
      : resultsTab,
  );
  const hasUnsavedChanges = $derived(openVersion !== null && editorCode !== openVersion.code);
  const versionItems = $derived(
    (strategy?.versions ?? []).map((version) => ({
      value: String(version.version_number),
      label: `v${String(version.version_number)}`,
    })),
  );
  const isEditorOnTop = $derived(paneOrder === 'editor-on-top');
  const topPanel = $derived<PanelId>(isEditorOnTop ? 'editor' : 'results');
  const bottomPanel = $derived<PanelId>(isEditorOnTop ? 'results' : 'editor');
  // The splitter works only while no panel is minimized or maximized.
  const isSplitterShown = $derived(
    panelSizes.results === 'normal' && panelSizes.editor === 'normal' && findMaximizedPanel(panelSizes) === null,
  );
  const paneRows = $derived(
    isSplitterShown
      ? `minmax(0, ${String(topFraction)}fr) auto minmax(0, ${String(1 - topFraction)}fr)`
      : `${findRowSize(topPanel)} ${findRowSize(bottomPanel)}`,
  );

  function findRowSize(id: PanelId): string {
    return isPanelCollapsed(panelSizes, id) ? 'auto' : 'minmax(0, 1fr)';
  }

  function changePanelSizes(sizes: PanelSizes): void {
    panelSizes = sizes;
    writePanelSizes(() => localStorage, sizes);
  }

  function openOutput(tab: OutputTab): void {
    outputTab = tab;
    changePanelSizes(openOutputPanel(panelSizes));
  }

  function restoreOnEscape(event: KeyboardEvent): void {
    const isDialogOpen = isBacktestDialogOpen || isForwardTestDialogOpen || isNewStrategyDialogOpen;
    if (event.key === 'Escape' && !isDialogOpen && findMaximizedPanel(panelSizes) !== null) {
      changePanelSizes(restoreMaximized(panelSizes));
    }
  }

  // Code completion and live type errors in the editor.
  const languageServer = connectStrategyLanguageServer(window.location);
  $effect(() => () => {
    languageServer.disconnect();
  });

  function writeOutput(line: string): void {
    const time = new Date().toISOString().slice('YYYY-MM-DDT'.length, 'YYYY-MM-DDTHH:MM:SS'.length);
    outputLines = [...outputLines, `${time}  ${line}`];
  }

  function readStrategyList(): void {
    void listStrategies(fetch).then((result) => {
      if (result.kind === 'failed') {
        listError = result.message;
        return;
      }
      strategies = result.value;
    });
  }

  function readBacktestList(): void {
    void listBacktests(fetch).then((result) => {
      if (result.kind === 'ok') {
        openFinishedBacktests(result.value);
        allBacktests = result.value;
      }
    });
  }

  // A backtest of this strategy that was running and is now final opens as the selected tab.
  function openFinishedBacktests(nextBacktests: Backtest[]): void {
    const finished = nextBacktests.find(
      (next) =>
        next.strategy_id === activeStrategyId &&
        isFinalStatus(next.status) &&
        allBacktests.some((previous) => previous.id === next.id && !isFinalStatus(previous.status)),
    );
    if (finished !== undefined) {
      resultsBacktestId = finished.id;
      resultsTab = backtestTab(finished.id);
      writeOutput(`Backtest ${String(finished.id)} ${finished.status === 'finished' ? 'finished' : finished.status}.`);
    }
  }

  $effect(() => {
    readStrategyList();
    readBacktestList();
  });

  $effect(() => {
    if (!hasRunningBacktest) {
      return;
    }
    const timer = setInterval(readBacktestList, BACKTEST_POLL_MILLISECONDS);
    return () => {
      clearInterval(timer);
    };
  });

  $effect(() =>
    openLiveSocket({
      url: buildSocketUrl(FORWARD_TESTS_SOCKET_PATH, window.location),
      onMessage: (message) => {
        const forwardTestsMessage = readForwardTestsMessage(message);
        if (forwardTestsMessage !== null) {
          forwardTests = forwardTestsMessage;
        }
      },
      onConnectionChange: () => {},
    }),
  );

  $effect(() => {
    const id = activeStrategyId;
    strategy = null;
    openVersion = null;
    problems = [];
    resultsTab = NEWEST_BACKTEST_TAB;
    resultsBacktestId = null;
    if (id !== null) {
      void loadStrategy(id, null);
    }
  });

  async function loadStrategy(id: number, versionNumberToOpen: number | null): Promise<void> {
    const result = await readStrategy(fetch, id);
    if (result.kind === 'failed') {
      writeOutput(result.message);
      return;
    }
    strategy = result.value;
    const versionNumber = versionNumberToOpen ?? result.value.versions.at(-1)?.version_number;
    if (versionNumber !== undefined) {
      await openStrategyVersion(id, versionNumber);
    }
  }

  async function openStrategyVersion(id: number, versionNumber: number): Promise<void> {
    const result = await readStrategyVersion(fetch, id, versionNumber);
    if (result.kind === 'failed') {
      writeOutput(result.message);
      return;
    }
    const draft = readDraft(localStorage, { strategyId: id, versionNumber });
    openVersion = result.value;
    editorCode = draft ?? result.value.code;
    problems = [];
  }

  function changeCode(code: string): void {
    editorCode = code;
    if (openVersion === null || activeStrategyId === null) {
      return;
    }
    const draftKey = { strategyId: activeStrategyId, versionNumber: openVersion.version_number };
    if (code === openVersion.code) {
      clearDraft(localStorage, draftKey);
    } else {
      writeDraft(localStorage, draftKey, code);
    }
  }

  async function saveVersion(): Promise<void> {
    if (openVersion === null || strategy === null || isSaving) {
      return;
    }
    const id = strategy.id;
    const baseVersionNumber = openVersion.version_number;
    isSaving = true;
    const result = await saveStrategyVersion(fetch, id, editorCode);
    isSaving = false;
    problems = [];
    if (result.kind === 'check_failed') {
      problems = result.problems;
      openOutput('problems');
      writeOutput(`Not saved: ${String(result.problems.length)} problems.`);
      return;
    }
    if (result.kind === 'failed') {
      writeOutput(result.message);
      return;
    }
    clearDraft(localStorage, { strategyId: id, versionNumber: baseVersionNumber });
    const label = formatVersionLabel(strategy.name, result.version.version_number);
    await loadStrategy(id, result.version.version_number);
    writeOutput(result.isNewVersion ? `Saved as ${label}.` : `Saved. The code is the same as ${label}.`);
  }

  function toggleForwardTest(): void {
    if (openVersion === null) {
      return;
    }
    if (runningForwardTest === null) {
      isForwardTestDialogOpen = true;
      return;
    }
    const forwardTestId = runningForwardTest.id;
    void stopForwardTest(fetch, forwardTestId).then((result) => {
      if (result.kind === 'failed') {
        writeOutput(result.message);
        return;
      }
      forwardTests = forwardTests.map((forwardTest) =>
        forwardTest.id === forwardTestId ? { ...forwardTest, desired_state: 'stopped' } : forwardTest,
      );
      writeOutput(`Forward test ${String(forwardTestId)}: stop requested.`);
    });
  }

  function openBacktestDialog(): void {
    if (openVersion !== null && runningBacktest === null) {
      isBacktestDialogOpen = true;
    }
  }

  function swapPanes(): void {
    paneOrder = isEditorOnTop ? 'results-on-top' : 'editor-on-top';
    writePaneOrder(() => localStorage, paneOrder);
  }

  function runShortcut(event: KeyboardEvent): void {
    restoreOnEscape(event);
    if (!(event.ctrlKey || event.metaKey)) {
      return;
    }
    const key = event.key.toLowerCase();
    const shortcuts: Record<string, (() => void) | undefined> = {
      s: () => void saveVersion(),
      b: openBacktestDialog,
      'shift+f': toggleForwardTest,
    };
    const action = shortcuts[event.shiftKey ? `shift+${key}` : key];
    if (action !== undefined) {
      event.preventDefault();
      action();
    }
  }

  function moveSplitter(event: PointerEvent): void {
    if (!isDraggingSplitter || paneStack === undefined) {
      return;
    }
    const stackBox = paneStack.getBoundingClientRect();
    topFraction = clampTopFraction((event.clientY - stackBox.top) / stackBox.height);
  }

  function moveSplitterWithKey(event: KeyboardEvent): void {
    const steps: Record<string, number | undefined> = { ArrowUp: -SPLITTER_KEY_STEP, ArrowDown: SPLITTER_KEY_STEP };
    const step = steps[event.key];
    if (step !== undefined) {
      event.preventDefault();
      topFraction = clampTopFraction(topFraction + step);
    }
  }

  async function submitNewStrategy(): Promise<void> {
    isCreating = true;
    const result = await createStrategy(fetch, newStrategyName);
    isCreating = false;
    if (result.kind === 'failed') {
      createError = result.message;
      return;
    }
    isNewStrategyDialogOpen = false;
    readStrategyList();
    await goto(resolve('/strategies/[strategyId]', { strategyId: String(result.strategy.id) }));
  }
</script>

<svelte:window onkeydown={runShortcut} />

{#snippet resultsPane()}
  <WorkbenchResultsPane
    backtests={strategyBacktests}
    tab={shownTab}
    backtestId={shownBacktestId}
    size={panelSizes.results}
    isCollapsed={isPanelCollapsed(panelSizes, 'results')}
    onToggleMinimized={() => {
      changePanelSizes(toggleMinimized(panelSizes, 'results'));
    }}
    onToggleMaximized={() => {
      changePanelSizes(toggleMaximized(panelSizes, 'results'));
    }}
    onTabChange={(tab: ResultsTab) => {
      resultsTab = tab;
      if (tab.startsWith('backtest-')) {
        resultsBacktestId = Number(tab.slice('backtest-'.length));
      }
    }}
  />
{/snippet}

{#snippet editorPane()}
  <WorkbenchEditorPane
    fileName="main.py"
    code={editorCode}
    editorKey={String(activeStrategyId)}
    extensions={[languageServer.editorExtension]}
    size={panelSizes.editor}
    isCollapsed={isPanelCollapsed(panelSizes, 'editor')}
    onCodeChange={changeCode}
    onToggleMinimized={() => {
      changePanelSizes(toggleMinimized(panelSizes, 'editor'));
    }}
    onToggleMaximized={() => {
      changePanelSizes(toggleMaximized(panelSizes, 'editor'));
    }}
  />
{/snippet}

<div class="workbench">
  <nav class="strategy-column" aria-labelledby="strategy-list-heading">
    <div class="column-header">
      <h1 id="strategy-list-heading" class="column-heading">Strategies</h1>
      <WorkbenchIconButton
        label="New strategy"
        icon={Add16}
        align="bottom-end"
        onclick={() => {
          newStrategyName = '';
          createError = '';
          isNewStrategyDialogOpen = true;
        }}
      />
    </div>
    <div class="list-area">
      <ScrollRegion label="Strategy list" maxHeight="100%">
        {#if listError !== ''}
          <p class="column-message">{listError}</p>
        {/if}
        <ul class="strategy-list">
          {#each strategies as item (item.id)}
            <li>
              <a
                class="strategy-row"
                href={resolve('/strategies/[strategyId]', { strategyId: String(item.id) })}
                aria-current={item.id === activeStrategyId ? 'page' : undefined}
              >
                <span class="strategy-name">{item.name}</span>
                <span class="strategy-version">v{item.latest_version_number}</span>
              </a>
            </li>
          {/each}
        </ul>
      </ScrollRegion>
    </div>
  </nav>

  <div class="main-area">
    {#if strategy !== null}
      <div class="toolbar">
        <h2 class="strategy-title">{strategy.name}</h2>
        <div class="version-select">
          <Select
            label="Version"
            items={versionItems}
            value={String(openVersion?.version_number ?? '')}
            onValueChange={(versionNumber: string) => {
              if (strategy !== null) {
                void openStrategyVersion(strategy.id, Number(versionNumber));
              }
            }}
          />
        </div>
        <div class="toolbar-actions">
          <WorkbenchIconButton
            label={isEditorOnTop ? 'Put editor at bottom' : 'Put editor on top'}
            icon={isEditorOnTop ? ArrowDown16 : ArrowUp16}
            onclick={swapPanes}
          />
          <WorkbenchIconButton
            label={hasUnsavedChanges ? 'Save version, unsaved changes' : 'Save version'}
            icon={Save16}
            shortcut="Ctrl+S"
            marked={hasUnsavedChanges}
            busy={isSaving}
            onclick={() => void saveVersion()}
          />
          {#if runningForwardTest === null}
            <WorkbenchIconButton
              label="Start forward test"
              icon={Radio16}
              tone="interactive"
              shortcut="Ctrl+Shift+F"
              onclick={toggleForwardTest}
            />
          {:else}
            <WorkbenchIconButton
              label="Stop forward test"
              icon={StopFilledAlt16}
              tone="error"
              shortcut="Ctrl+Shift+F"
              onclick={toggleForwardTest}
            />
          {/if}
          {#if runningBacktest === null}
            <WorkbenchIconButton
              label="Run backtest"
              icon={PlayFilledAlt16}
              tone="success"
              shortcut="Ctrl+B"
              align="bottom-end"
              onclick={openBacktestDialog}
            />
          {:else}
            <WorkbenchIconButton
              label="Backtest is running"
              icon={InProgress16}
              tone="warning"
              align="bottom-end"
              busy
              onclick={() => {}}
            />
          {/if}
        </div>
      </div>

      <div
        class={['pane-stack', isDraggingSplitter && 'dragging', panelSizes.output === 'maximized' && 'shrunk']}
        bind:this={paneStack}
        style:grid-template-rows={paneRows}
      >
        <div class="pane">
          {@render (isEditorOnTop ? editorPane : resultsPane)()}
        </div>
        {#if isSplitterShown}
        <!-- A focusable separator is the WAI-ARIA window splitter pattern: the arrow keys move it. -->
        <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
        <div
          class="splitter"
          role="separator"
          tabindex="0"
          aria-label="Resize panes"
          aria-orientation="horizontal"
          aria-valuemin={0}
          aria-valuemax={PERCENT}
          aria-valuenow={Math.round(topFraction * PERCENT)}
          onpointerdown={(event: PointerEvent) => {
            if (event.currentTarget instanceof HTMLElement) {
              event.currentTarget.setPointerCapture(event.pointerId);
            }
            isDraggingSplitter = true;
          }}
          onpointermove={moveSplitter}
          onpointerup={() => (isDraggingSplitter = false)}
          onpointercancel={() => (isDraggingSplitter = false)}
          onkeydown={moveSplitterWithKey}
        ></div>
        {/if}
        <div class="pane">
          {@render (isEditorOnTop ? resultsPane : editorPane)()}
        </div>
      </div>
      <WorkbenchOutputPanel
        {problems}
        {outputLines}
        size={panelSizes.output}
        isVisible={!isPanelCollapsed(panelSizes, 'output')}
        tab={outputTab}
        onOpen={openOutput}
        onTabChange={(tab: OutputTab) => {
          outputTab = tab;
        }}
        onToggleMinimized={() => {
          changePanelSizes({ ...restoreMaximized(panelSizes), output: 'minimized' });
        }}
        onToggleMaximized={() => {
          changePanelSizes(toggleMaximized(panelSizes, 'output'));
        }}
      />
    {:else if strategies.length === 0 && listError === ''}
      <p class="main-message">No strategy yet.</p>
    {/if}
  </div>
</div>

<WorkbenchBacktestDialog
  open={isBacktestDialogOpen}
  title={strategy === null || openVersion === null ? 'Run backtest' : `Run backtest of ${formatVersionLabel(strategy.name, openVersion.version_number)}`}
  strategyVersionId={openVersion?.id ?? null}
  onOpenChange={(open: boolean) => {
    isBacktestDialogOpen = open;
  }}
  onStarted={(backtest: Backtest) => {
    allBacktests = [backtest, ...allBacktests];
    writeOutput(`Backtest ${String(backtest.id)} queued.`);
  }}
/>

<WorkbenchForwardTestDialog
  open={isForwardTestDialogOpen}
  title={strategy === null || openVersion === null ? 'Start forward test' : `Start forward test of ${formatVersionLabel(strategy.name, openVersion.version_number)}`}
  strategyVersionId={openVersion?.id ?? null}
  onOpenChange={(open: boolean) => {
    isForwardTestDialogOpen = open;
  }}
  onStarted={(forwardTest: ForwardTest) => {
    forwardTests = [forwardTest, ...forwardTests.filter((item) => item.id !== forwardTest.id)];
    writeOutput(`Forward test ${String(forwardTest.id)} started.`);
  }}
/>

<Dialog
  open={isNewStrategyDialogOpen}
  onOpenChange={(open: boolean) => {
    isNewStrategyDialogOpen = open;
  }}
  title="New strategy"
  primaryText="Create strategy"
  busy={isCreating}
  onPrimary={() => {
    void submitNewStrategy();
  }}
>
  <TextInput label="Strategy name" bind:value={newStrategyName} required maxlength={STRATEGY_NAME_MAX_LENGTH} />
  {#if createError !== ''}
    <InlineNotification kind="error" lowContrast title="Strategy not created" subtitle={createError} />
  {/if}
</Dialog>

<style>
  .workbench {
    display: grid;
    grid-template-columns: calc(3 * var(--cds-spacing-12) - var(--cds-spacing-06)) minmax(0, 1fr);
    block-size: 100%;
    min-block-size: 0;
    background: var(--cds-background);
  }

  .strategy-column {
    display: flex;
    flex-direction: column;
    min-block-size: 0;
    border-inline-end: 1px solid var(--cds-border-subtle-01);
  }

  .column-header,
  .toolbar {
    display: flex;
    flex: none;
    align-items: center;
    block-size: var(--cds-spacing-07);
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .column-heading,
  .strategy-title {
    flex: 1;
    min-inline-size: 0;
    margin: 0;
    padding-inline-start: var(--cds-spacing-05);
    overflow: hidden;
    font-size: var(--cds-heading-compact-01-font-size);
    font-weight: var(--cds-heading-compact-01-font-weight);
    line-height: var(--cds-heading-compact-01-line-height);
    letter-spacing: var(--cds-heading-compact-01-letter-spacing);
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .strategy-title {
    flex: 0 1 auto;
  }

  .list-area {
    position: relative;
    flex: 1;
    min-block-size: 0;
  }

  .list-area :global(.scroll-region) {
    position: absolute;
    inset: 0;
  }

  .strategy-list {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .strategy-row {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
    block-size: var(--cds-spacing-07);
    padding-inline: var(--cds-spacing-05) var(--cds-spacing-03);
    border-inline-start: 3px solid transparent;
    color: var(--cds-text-secondary);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    text-decoration: none;
  }

  .strategy-row:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-primary);
  }

  .strategy-row:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .strategy-row[aria-current='page'] {
    border-inline-start-color: var(--cds-border-interactive);
    background: var(--cds-layer-selected-01);
    color: var(--cds-text-primary);
    font-weight: 600;
  }

  .strategy-name {
    flex: 1;
    min-inline-size: 0;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .strategy-version {
    flex: none;
    color: var(--cds-text-secondary);
    font-variant-numeric: tabular-nums;
  }

  .column-message,
  .main-message {
    margin: 0;
    padding: var(--cds-spacing-05);
    color: var(--cds-text-secondary);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
  }

  .main-area {
    display: flex;
    flex-direction: column;
    min-inline-size: 0;
    min-block-size: 0;
  }

  .version-select {
    flex: none;
    inline-size: var(--cds-spacing-12);
    margin-inline-start: var(--cds-spacing-03);
  }

  /* The toolbar layout names the select: its label is only for screen readers. */
  .version-select :global(.cds--label) {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }

  .version-select :global(.cds--list-box) {
    block-size: var(--cds-spacing-07);
    max-block-size: var(--cds-spacing-07);
    border-block-end: 0;
    background: transparent;
  }

  .toolbar-actions {
    display: flex;
    margin-inline-start: auto;
  }

  .pane-stack {
    display: grid;
    flex: 1;
    min-block-size: 0;
  }

  .pane-stack.shrunk {
    flex: none;
  }

  .pane-stack.dragging {
    cursor: row-resize;
    user-select: none;
  }

  .pane {
    min-block-size: 0;
    overflow: hidden;
  }

  .splitter {
    block-size: var(--cds-spacing-02);
    background: var(--cds-border-subtle-01);
    cursor: row-resize;
    touch-action: none;
  }

  .splitter:hover,
  .splitter:focus-visible,
  .dragging .splitter {
    background: var(--cds-border-interactive);
    outline: none;
  }
</style>
