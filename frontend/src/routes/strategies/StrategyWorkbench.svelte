<!-- Strategy page: a workbench (foundation/workbench, spec #99, ticket #106) like the QuantConnect editor. URL:
     /strategies/<id> opens the latest version that is not discarded; /strategies/<id>/versions/<n> opens version n, and then the address
     follows the open version; /strategies opens the first strategy of the list.
     Left: the "Strategies" side column with the "New strategy" button. Center: the toolbar line (strategy name, version,
     "Show discarded versions" when the strategy has a discarded version, and icon buttons with the state in their icon and color), then the results panel and the editor panel with a
     splitter between them. The swap button puts the editor on top or at the bottom; the browser keeps the choice.
     Run backtest and Start forward test open the dialogs of the backtest page and the forward test page with the
     open version. The results panel has one tab for each backtest of the strategy (number and total return), then Trades, Orders,
     and Logs. A backtest that ends opens in its tab. The editor panel has the file tab and the code editor. Unsaved
     edits stay in localStorage (drafts of the strategy capability).
     Below the two panels is the problems and output panel (ticket #107, like the VS Code panel). It starts minimized
     to its 24px status bar: the error and warning counts open the Problems tab, "Output" opens the Output tab. A click
     on the selected tab minimizes it again. A save that the code checks refuse opens Problems; a click on a problem goes
     to its line in the editor. Output lists the events and errors of saves, backtests, forward tests, and the AI
     assistant.
     Right: the "AI assistant" side column (AssistantColumn, docs/architecture/assistant.md 25.12). A click on a diff
     card opens a diff tab in the editor panel; Keep opens the new version, Discard keeps the open version. Maximize of
     the side column hides the center area: it shows only a 32px rail. -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import ErrorFilled16 from '@carbon/icons/es/error--filled/16.js';
  import WarningAltFilled16 from '@carbon/icons/es/warning--alt--filled/16.js';
  import ArrowDown16 from '@carbon/icons/es/arrow--down/16.js';
  import ArrowUp16 from '@carbon/icons/es/arrow--up/16.js';
  import ConnectionSignal16 from '@carbon/icons/es/connection-signal/16.js';
  import InProgress16 from '@carbon/icons/es/in-progress/16.js';
  import PlayFilledAlt16 from '@carbon/icons/es/play--filled--alt/16.js';
  import Save16 from '@carbon/icons/es/save/16.js';
  import StopFilledAlt16 from '@carbon/icons/es/stop--filled--alt/16.js';
  import TrashCan16 from '@carbon/icons/es/trash-can/16.js';
  import { untrack } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { resolve } from '$app/paths';
  import { isFinalStatus, listBacktests, type Backtest } from '#lib/backtest';
  import { Dialog, Icon, IconButton, InlineNotification, Select, TextInput, Toggle } from '#lib/foundation/carbon';
  import { CodeDiff, CodeEditor } from '#lib/foundation/code_editor';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { LiveUpdatesNotification } from '#lib/foundation/live_socket';
  import { startPolling } from '#lib/foundation/polling';
  import { ChangeText } from '#lib/foundation/value_format';
  import {
    Panel,
    PanelHeader,
    PanelSplit,
    readStoredLayout,
    SideColumn,
    Workbench,
    writeStoredLayout,
  } from '#lib/foundation/workbench';
  import { ForwardTestsOnInstrumentsFeed, stopForwardTest, type ForwardTest } from '#lib/forward_test';
  import {
    clearDraft,
    connectStrategyLanguageServer,
    createStrategy,
    deleteStrategy,
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
    type StrategyVersionKey,
  } from '#lib/strategy';
  import StartBacktestDialog from '../backtests/StartBacktestDialog.svelte';
  import StartForwardTestDialog from '../forward-tests/StartForwardTestDialog.svelte';
  import AssistantColumn from './AssistantColumn.svelte';
  import StrategyList from './StrategyList.svelte';
  import StrategyOutput from './StrategyOutput.svelte';
  import StrategyResults from './StrategyResults.svelte';
  import {
    createBacktestTab,
    createOutputLine,
    describeBacktestEvent,
    describeProblemCounts,
    describeShortcut,
    describeSwapButton,
    findDefaultVersionNumber,
    findFinishedBacktest,
    findRunningForwardTest,
    isMacPlatform,
    listResultTabs,
    listVersionItems,
    listWorkbenchPanels,
    PANE_ORDER_STORAGE_KEY,
    readPaneOrder,
    readWorkbenchShortcut,
    resolveResultTab,
    selectStrategyBacktests,
    swapPaneOrder,
    type OutputTab,
    type PaneOrder,
    type ResultSelection,
    type ResultTab,
    type WorkbenchShortcut,
  } from './strategy_workbench';

  // versionNumber comes from the version address /strategies/<id>/versions/<n>. Without it, the latest version that is
  // not discarded opens.
  const {
    strategyId,
    versionNumber: addressVersionNumber = null,
  }: { strategyId: number | null; versionNumber?: number | null } = $props();

  // The backend refuses a longer name.
  const STRATEGY_NAME_MAX_LENGTH = 100;
  const LIST_CHECK_INTERVAL_MILLISECONDS = 2000;
  const FILE_TAB = { value: 'strategy', label: 'strategy.py' };
  const DIFF_TAB_VALUE = 'diff';
  const isMac = isMacPlatform(navigator);

  let strategies: StrategyListItem[] = $state([]);
  let listMessage = $state('');
  // The read error of the open strategy. No panel shows it (the panels need the strategy), so the main area does.
  let strategyMessage = $state('');
  // A new value reads the strategy list again, for example after a save.
  let listReadCount = $state(0);
  let strategy = $state<StrategyDetail | null>(null);
  let openVersion = $state<StrategyVersion | null>(null);
  // "Show discarded versions": the version Select hides the discarded versions until the user turns it on.
  let showDiscarded = $state(false);
  let editorCode = $state('');
  let problems: CodeProblem[] = $state([]);
  let outputLines: string[] = $state([]);
  let outputTab = $state<OutputTab>('problems');
  // The exported functions of the panel split and the code editor (bind:this).
  let panelSplit: { openPanel: (id: string) => void } | undefined = $state();
  let codeEditor: { revealLine: (line: number) => void } | undefined = $state();
  let isSaving = $state(false);
  let backtests: Backtest[] = $state([]);
  // A new value reads the backtest list again, for example after a new backtest starts.
  let backtestReadCount = $state(0);
  let selection = $state<ResultSelection>({ tab: null, backtestId: null });
  let paneOrder = $state<PaneOrder>(readPaneOrder(readStoredLayout(PANE_ORDER_STORAGE_KEY)));
  let isStoppingForwardTest = $state(false);
  let isNewStrategyDialogOpen = $state(false);
  let newStrategyName = $state('');
  let createMessage = $state('');
  let isCreating = $state(false);
  let isDeleteDialogOpen = $state(false);
  let isDeleting = $state(false);
  let isBacktestDialogOpen = $state(false);
  let isForwardTestDialogOpen = $state(false);
  let newStrategyForm: HTMLFormElement | undefined = $state();
  // The diff of a diff card of the AI assistant: the new version and the version before it.
  let diff = $state<{ versionNumber: number; firstCode: string; secondCode: string } | null>(null);
  let editorTab = $state(FILE_TAB.value);
  let isAssistantMaximized = $state(false);

  const forwardTestFeed = new ForwardTestsOnInstrumentsFeed();
  $effect(() => forwardTestFeed.start(window.location));

  // Code completion and live type errors. Type errors do not block the save.
  const languageServer = connectStrategyLanguageServer(window.location);
  $effect(() => () => {
    languageServer.disconnect();
  });

  const activeStrategyId = $derived(strategyId ?? strategies[0]?.id ?? null);
  const resultTabs = $derived(listResultTabs(backtests, activeStrategyId));
  const shownResult = $derived(resolveResultTab(selection, backtests, activeStrategyId));
  const shownBacktest = $derived(backtests.find((backtest) => backtest.id === shownResult.backtestId) ?? null);
  const runningBacktest = $derived(
    selectStrategyBacktests(backtests, activeStrategyId).find((backtest) => !isFinalStatus(backtest.status)) ?? null,
  );
  const runningForwardTest = $derived(findRunningForwardTest(forwardTestFeed.forwardTests, activeStrategyId));
  const hasUnsavedChanges = $derived(openVersion !== null && editorCode !== openVersion.code);
  const versionItems = $derived(
    listVersionItems(strategy?.versions ?? [], {
      showDiscarded,
      openVersionNumber: openVersion?.version_number ?? null,
    }),
  );
  const hasDiscardedVersion = $derived((strategy?.versions ?? []).some((version) => version.discarded));
  const openVersionKey = $derived<StrategyVersionKey | null>(
    openVersion === null ? null : { strategyId: openVersion.strategy_id, versionId: openVersion.id },
  );
  const fileTabs = $derived(
    diff === null
      ? [FILE_TAB]
      : [FILE_TAB, { value: DIFF_TAB_VALUE, label: `v${String(diff.versionNumber - 1)} → v${String(diff.versionNumber)}` }],
  );
  const problemCounts = $derived(describeProblemCounts(problems));
  const swapButton = $derived(describeSwapButton(paneOrder));
  const panels = $derived(listWorkbenchPanels(paneOrder));
  const isDialogOpen = $derived(
    isNewStrategyDialogOpen || isDeleteDialogOpen || isBacktestDialogOpen || isForwardTestDialogOpen,
  );

  $effect(() => {
    const readNumber = listReadCount;
    void listStrategies(fetch).then((result) => {
      if (readNumber !== listReadCount) {
        return;
      }
      if (result.kind === 'failed') {
        listMessage = result.message;
        return;
      }
      listMessage = '';
      strategies = result.value;
    });
  });

  // The backtest list reads again while a backtest in it is queued or running. A backtest of this strategy that ends
  // opens in its tab.
  $effect(() => {
    // A new read count runs this effect again: its cleanup stops the old loop.
    backtestReadCount satisfies number;
    // A failed read writes one Output line (not again for each retry), and the list reads again. It does not open the
    // panel: a reload aborts the read, and an open panel would be stored in the layout of the next page.
    let failureText = '';
    function showFailure(message: string): void {
      const text = `Backtests not read: ${message}`;
      if (text !== failureText) {
        failureText = text;
        writeOutput(text);
      }
    }
    return startPolling(
      () => listBacktests(fetch),
      (result) => {
        if (result.kind === 'failed') {
          showFailure(result.message);
          return true;
        }
        failureText = '';
        const finished = findFinishedBacktest(backtests, result.value, activeStrategyId);
        if (finished !== null) {
          selection = { tab: createBacktestTab(finished.id), backtestId: finished.id };
          writeOutput(describeBacktestEvent(finished));
        }
        backtests = result.value;
        return result.value.some((item) => !isFinalStatus(item.status));
      },
      LIST_CHECK_INTERVAL_MILLISECONDS,
      showFailure,
    );
  });

  $effect(() => {
    const id = activeStrategyId;
    strategy = null;
    strategyMessage = '';
    openVersion = null;
    problems = [];
    selection = { tab: null, backtestId: null };
    diff = null;
    editorTab = FILE_TAB.value;
    if (id !== null) {
      // The address gives the first version only. A later version change writes the address (openStrategyVersion).
      void loadStrategy(
        id,
        untrack(() => addressVersionNumber),
      );
    }
  });

  async function loadStrategy(id: number, versionNumberToOpen: number | null): Promise<void> {
    const result = await readStrategy(fetch, id);
    if (result.kind === 'failed') {
      strategyMessage = result.message;
      writeOutputError(`Strategy not read: ${result.message}`);
      return;
    }
    strategyMessage = '';
    strategy = result.value;
    const versionNumber = versionNumberToOpen ?? findDefaultVersionNumber(result.value.versions);
    if (versionNumber !== undefined) {
      await openStrategyVersion(id, versionNumber);
    }
  }

  async function openStrategyVersion(id: number, versionNumber: number): Promise<void> {
    const result = await readStrategyVersion(fetch, id, versionNumber);
    if (result.kind === 'failed') {
      writeOutputError(`Version not read: ${result.message}`);
      return;
    }
    const draft = readDraft(localStorage, { strategyId: id, versionNumber });
    openVersion = result.value;
    editorCode = draft ?? result.value.code;
    problems = [];
    // On a version address, the address names the open version, so that a reload opens it again. The shallow route
    // change keeps the workbench state.
    if (addressVersionNumber !== null) {
      const href = resolve('/strategies/[strategyId]/versions/[versionNumber]', {
        strategyId: String(id),
        versionNumber: String(versionNumber),
      });
      if (page.url.pathname !== href) {
        await goto(href, { state: page.state, shallow: true, replace: true });
      }
    }
  }

  function changeCode(code: string): void {
    editorCode = code;
    if (openVersion === null) {
      return;
    }
    const draftKey = { strategyId: openVersion.strategy_id, versionNumber: openVersion.version_number };
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
    const name = strategy.name;
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
      writeOutputError(`Version not saved: ${result.message}`);
      return;
    }
    clearDraft(localStorage, { strategyId: id, versionNumber: baseVersionNumber });
    const label = formatVersionLabel(name, result.version.version_number);
    await loadStrategy(id, result.version.version_number);
    listReadCount += 1;
    writeOutput(result.isNewVersion ? `Saved as ${label}.` : `Saved. The code is the same as ${label}.`);
  }

  async function openDiff(versionNumber: number): Promise<void> {
    if (strategy === null) {
      return;
    }
    const id = strategy.id;
    const [before, after] = await Promise.all([
      readStrategyVersion(fetch, id, versionNumber - 1),
      readStrategyVersion(fetch, id, versionNumber),
    ]);
    if (before.kind === 'failed' || after.kind === 'failed') {
      writeOutputError(`Diff not read: ${before.kind === 'failed' ? before.message : after.kind === 'failed' ? after.message : ''}`);
      return;
    }
    diff = { versionNumber, firstCode: before.value.code, secondCode: after.value.code };
    editorTab = DIFF_TAB_VALUE;
    panelSplit?.openPanel('editor');
  }

  function closeDiff(versionNumber: number): void {
    if (diff?.versionNumber === versionNumber) {
      diff = null;
      editorTab = FILE_TAB.value;
    }
  }

  // Keep: the editor opens the new version (docs/architecture/assistant.md 25.5.2).
  async function keepVersion(versionNumber: number): Promise<void> {
    if (strategy === null) {
      return;
    }
    closeDiff(versionNumber);
    await loadStrategy(strategy.id, versionNumber);
    writeOutput(`Kept ${formatVersionLabel(strategy.name, versionNumber)}.`);
  }

  // Discard: the editor stays on the open version. The version list reads the discarded mark again.
  async function showDiscardedVersion(versionNumber: number): Promise<void> {
    if (strategy === null) {
      return;
    }
    closeDiff(versionNumber);
    const label = formatVersionLabel(strategy.name, versionNumber);
    const result = await readStrategy(fetch, strategy.id);
    if (result.kind === 'ok') {
      strategy = result.value;
    }
    writeOutput(`Discarded ${label}.`);
  }

  function writeOutput(text: string): void {
    outputLines = [...outputLines, createOutputLine(new Date(), text)];
  }

  // An error opens the Output tab, so it shows also while the panel is minimized to its status bar.
  function writeOutputError(text: string): void {
    writeOutput(text);
    openOutput('output');
  }

  // A status bar control or a refused save: the panel opens above the status bar at the tab.
  function openOutput(tab: OutputTab): void {
    outputTab = tab;
    panelSplit?.openPanel('output');
  }

  function revealProblem(problem: CodeProblem): void {
    codeEditor?.revealLine(problem.line);
  }

  function swapPanels(): void {
    paneOrder = swapPaneOrder(paneOrder);
    writeStoredLayout(PANE_ORDER_STORAGE_KEY, paneOrder);
  }

  function openBacktestDialog(): void {
    if (openVersion !== null && runningBacktest === null) {
      isBacktestDialogOpen = true;
    }
  }

  async function toggleForwardTest(): Promise<void> {
    if (openVersion === null || isStoppingForwardTest) {
      return;
    }
    if (runningForwardTest === null) {
      isForwardTestDialogOpen = true;
      return;
    }
    isStoppingForwardTest = true;
    const forwardTestId = runningForwardTest.id;
    const result = await stopForwardTest(fetch, forwardTestId);
    isStoppingForwardTest = false;
    if (result.kind === 'failed') {
      writeOutputError(`Forward test #${String(forwardTestId)} not stopped: ${result.message}`);
      return;
    }
    writeOutput(`Forward test #${String(forwardTestId)} stop requested.`);
    // The socket pushes the list again later. The button shows the stop request at once.
    forwardTestFeed.forwardTests = forwardTestFeed.forwardTests.map((item) =>
      item.id === forwardTestId ? { ...item, desired_state: 'stopped' } : item,
    );
  }

  const SHORTCUT_ACTIONS: Record<WorkbenchShortcut, () => void> = {
    save: () => void saveVersion(),
    backtest: openBacktestDialog,
    'forward-test': () => void toggleForwardTest(),
  };

  // Ctrl S, Ctrl B, and Ctrl Shift F (Cmd on macOS) also work in the editor: the editor uses none of these keys.
  function runShortcut(event: KeyboardEvent): void {
    const shortcut = readWorkbenchShortcut(event, isMac);
    if (shortcut === null || isDialogOpen || strategy === null) {
      return;
    }
    event.preventDefault();
    SHORTCUT_ACTIONS[shortcut]();
  }

  function selectResultTab(value: string): void {
    const tab = value as ResultTab;
    const backtestId = resultTabs.find((item) => item.value === tab)?.backtestId ?? null;
    selection = { tab, backtestId: backtestId ?? shownResult.backtestId };
  }

  function openNewStrategyDialog(): void {
    newStrategyName = '';
    createMessage = '';
    isNewStrategyDialogOpen = true;
  }

  async function submitNewStrategy(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    isCreating = true;
    const result = await createStrategy(fetch, newStrategyName);
    isCreating = false;
    if (result.kind === 'failed') {
      createMessage = result.message;
      return;
    }
    isNewStrategyDialogOpen = false;
    listReadCount += 1;
    await goto(resolve('/strategies/[strategyId]', { strategyId: String(result.strategy.id) }));
  }

  async function removeStrategy(): Promise<void> {
    if (strategy === null) {
      return;
    }
    isDeleting = true;
    const result = await deleteStrategy(fetch, strategy.id);
    isDeleting = false;
    isDeleteDialogOpen = false;
    if (result.kind === 'failed') {
      writeOutputError(`Strategy not deleted: ${result.message}`);
      return;
    }
    listReadCount += 1;
    await goto(resolve('/strategies'));
  }
</script>

<svelte:window onkeydown={runShortcut} />

{#snippet resultTabLabel(item: { value: string; label: string })}
  {@const tab = resultTabs.find((candidate) => candidate.value === item.value)}
  {#if tab === undefined || tab.changeText === ''}
    {item.label}
  {:else}
    <span class="result-tab-label">
      {tab.name}
      <ChangeText value={tab.change} text={tab.changeText} />
    </span>
  {/if}
{/snippet}

<Workbench>
  <SideColumn label="Strategies" side="start" storageKey="atrade.strategy-page.list-column">
    {#snippet actions()}
      <IconButton label="New strategy" icon={Add16} onclick={openNewStrategyDialog} />
    {/snippet}
    <StrategyList {strategies} errorMessage={listMessage} openStrategyId={activeStrategyId} />
  </SideColumn>

  <div class={['main', isAssistantMaximized && 'main--rail']}>
    {#if strategy !== null}
      {@const shownStrategy = strategy}
      <PanelHeader>
        <h1 class="strategy-name">{shownStrategy.name}</h1>
        <div class="version-select">
          <Select
            label="Version"
            hideLabel
            size="sm"
            items={versionItems}
            value={String(openVersion?.version_number ?? '')}
            onValueChange={(versionNumber: string) => {
              void openStrategyVersion(shownStrategy.id, Number(versionNumber));
            }}
          />
        </div>
        {#if hasDiscardedVersion}
          <Toggle
            label="Show discarded versions"
            checked={showDiscarded}
            onCheckedChange={(checked: boolean) => {
              showDiscarded = checked;
            }}
          />
        {/if}
        {#snippet end()}
          <IconButton
            label="Delete strategy"
            icon={TrashCan16}
            tone="neutral"
            onclick={() => {
              isDeleteDialogOpen = true;
            }}
          />
          <IconButton
            label={swapButton.label}
            icon={swapButton.direction === 'up' ? ArrowUp16 : ArrowDown16}
            tone="neutral"
            onclick={swapPanels}
          />
          <IconButton
            label={isSaving ? 'Saving version…' : hasUnsavedChanges ? 'Save version, unsaved changes' : 'Save version'}
            icon={Save16}
            tone="neutral"
            shortcut={describeShortcut('save', isMac)}
            marked={hasUnsavedChanges}
            disabled={isSaving}
            onclick={() => void saveVersion()}
          />
          {#if runningForwardTest === null}
            <IconButton
              label="Start forward test"
              icon={ConnectionSignal16}
              tone="interactive"
              shortcut={describeShortcut('forward-test', isMac)}
              onclick={() => void toggleForwardTest()}
            />
          {:else}
            <IconButton
              label={isStoppingForwardTest ? 'Stopping forward test…' : 'Stop forward test'}
              icon={StopFilledAlt16}
              tone="error"
              shortcut={describeShortcut('forward-test', isMac)}
              disabled={isStoppingForwardTest}
              onclick={() => void toggleForwardTest()}
            />
          {/if}
          {#if runningBacktest === null}
            <IconButton
              label="Run backtest"
              icon={PlayFilledAlt16}
              tone="success"
              align="bottom-end"
              shortcut={describeShortcut('backtest', isMac)}
              onclick={openBacktestDialog}
            />
          {:else}
            <IconButton
              label="Backtest is running"
              icon={InProgress16}
              tone="warning"
              align="bottom-end"
              disabled
              busy
              onclick={() => {}}
            />
          {/if}
        {/snippet}
      </PanelHeader>
      <LiveUpdatesNotification isConnected={forwardTestFeed.isConnected} />

      <PanelSplit storageKey="atrade.strategy-page.panel-split" {panels} bind:this={panelSplit}>
        {#snippet panel(id, state)}
          {#if id === 'results'}
            <Panel
              {...state}
              label="Results"
              tabs={{
                label: 'Results',
                items: resultTabs,
                value: shownResult.tab,
                onValueChange: selectResultTab,
                itemLabel: resultTabLabel,
              }}
            >
              <StrategyResults backtest={shownBacktest} tab={shownResult.tab} />
            </Panel>
          {:else if id === 'editor'}
            <Panel
              {...state}
              label="Editor"
              tabs={{
                label: 'Files',
                items: fileTabs,
                value: editorTab,
                onValueChange: (value: string) => {
                  editorTab = value;
                },
              }}
            >
              {#if diff !== null && editorTab === DIFF_TAB_VALUE}
                <CodeDiff
                  firstCode={diff.firstCode}
                  secondCode={diff.secondCode}
                  firstLabel={`v${String(diff.versionNumber - 1)}`}
                  secondLabel={`v${String(diff.versionNumber)}`}
                  fill
                />
              {/if}
              {#if openVersion !== null}
                <div class="editor" hidden={diff !== null && editorTab === DIFF_TAB_VALUE}>
                  {#key shownStrategy.id}
                    <CodeEditor
                      bind:this={codeEditor}
                      code={editorCode}
                      label="Strategy code"
                      onCodeChange={changeCode}
                      extensions={[languageServer.editorExtension]}
                    />
                  {/key}
                </div>
              {/if}
            </Panel>
          {:else}
            <Panel
              {...state}
              label="Problems and output"
              tabs={{
                label: 'Problems and output',
                items: [
                  { value: 'problems', label: `Problems ${String(problemCounts.errors)}` },
                  { value: 'output', label: 'Output' },
                ],
                value: outputTab,
                onValueChange: (value: string) => {
                  outputTab = value === 'output' ? 'output' : 'problems';
                },
              }}
            >
              {#snippet statusBar()}
                <button
                  type="button"
                  class="atrade-status-bar__item"
                  aria-label={problemCounts.label}
                  onclick={() => {
                    openOutput('problems');
                  }}
                >
                  <span class={['status-count', problemCounts.errors > 0 && 'status-count--error']}>
                    <Icon icon={ErrorFilled16} />{problemCounts.errors}
                  </span>
                  <span class={['status-count', problemCounts.warnings > 0 && 'status-count--warning']}>
                    <Icon icon={WarningAltFilled16} />{problemCounts.warnings}
                  </span>
                </button>
                <button
                  type="button"
                  class="atrade-status-bar__item"
                  onclick={() => {
                    openOutput('output');
                  }}
                >
                  Output
                </button>
              {/snippet}
              <StrategyOutput tab={outputTab} {problems} {outputLines} onProblemClick={revealProblem} />
            </Panel>
          {/if}
        {/snippet}
      </PanelSplit>
    {:else if strategyMessage !== ''}
      <InlineNotification kind="error" title="Strategy not read" subtitle={strategyMessage} lowContrast />
    {:else if strategies.length === 0 && listMessage === '' && strategyId === null}
      <EmptyText text="No strategies" />
    {/if}
  </div>

  {#if strategy !== null}
    <AssistantColumn
      strategyId={strategy.id}
      openVersionNumber={openVersion?.version_number ?? null}
      onOpenDiff={(versionNumber: number) => void openDiff(versionNumber)}
      onKeep={(versionNumber: number) => void keepVersion(versionNumber)}
      onDiscarded={(versionNumber: number) => void showDiscardedVersion(versionNumber)}
      onError={writeOutputError}
      onMaximizedChange={(isMaximized: boolean) => {
        isAssistantMaximized = isMaximized;
      }}
    />
  {/if}
</Workbench>

<Dialog
  open={isNewStrategyDialogOpen}
  onOpenChange={(open: boolean) => {
    isNewStrategyDialogOpen = open;
  }}
  title="New strategy"
  primaryText={isCreating ? 'Creating…' : 'Create strategy'}
  busy={isCreating}
  onPrimary={() => newStrategyForm?.requestSubmit()}
>
  <form class="new-strategy-form" aria-label="New strategy" bind:this={newStrategyForm} onsubmit={submitNewStrategy}>
    <TextInput label="Strategy name" name="name" bind:value={newStrategyName} required maxlength={STRATEGY_NAME_MAX_LENGTH} />
  </form>
  {#if createMessage !== ''}
    <InlineNotification kind="error" lowContrast title="Strategy not created" subtitle={createMessage} />
  {/if}
</Dialog>

{#if strategy !== null}
  <Dialog
    open={isDeleteDialogOpen}
    onOpenChange={(open: boolean) => {
      isDeleteDialogOpen = open;
    }}
    title="Delete {strategy.name}"
    primaryText="Delete strategy"
    primaryKind="danger"
    busy={isDeleting}
    onPrimary={() => {
      void removeStrategy();
    }}
  >
    <p>All versions of the strategy are deleted.</p>
  </Dialog>
{/if}

<StartBacktestDialog
  open={isBacktestDialogOpen}
  onOpenChange={(open: boolean) => {
    isBacktestDialogOpen = open;
  }}
  strategyVersion={openVersionKey}
  onStarted={(started: Backtest) => {
    // The new backtest opens in its tab at once; it shows its status until it ends.
    selection = { tab: createBacktestTab(started.id), backtestId: started.id };
    backtestReadCount += 1;
    writeOutput(describeBacktestEvent(started));
  }}
/>

<StartForwardTestDialog
  open={isForwardTestDialogOpen}
  onOpenChange={(open: boolean) => {
    isForwardTestDialogOpen = open;
  }}
  strategyVersion={openVersionKey}
  onStarted={(forwardTest: ForwardTest) => {
    writeOutput(`Forward test #${String(forwardTest.id)} started.`);
    // The socket pushes the list again later. The button shows the running forward test at once.
    forwardTestFeed.forwardTests = [forwardTest, ...forwardTestFeed.forwardTests.filter((item) => item.id !== forwardTest.id)];
  }}
/>

<style>
  .main {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-inline-size: 0;
    min-block-size: 0;
  }

  /* Maximize of the AI assistant: the center area is a 32px rail, and its content stays in the page. */
  .main--rail {
    flex: none;
    inline-size: var(--cds-spacing-07);
    border-inline-end: 1px solid var(--cds-border-subtle-01);
    overflow: hidden;
  }

  .main--rail > :global(*) {
    display: none;
  }

  .editor[hidden] {
    display: none;
  }

  .strategy-name {
    flex: 0 1 auto;
    min-inline-size: 0;
  }

  .version-select {
    flex: none;
    /* Room for "v123" and the tag "Discarded". */
    inline-size: calc(var(--cds-spacing-13) + var(--cds-spacing-07));
  }

  .main :global(.cds--inline-notification) {
    flex: none;
    max-inline-size: none;
    margin-block: 0;
  }

  .result-tab-label {
    display: inline-flex;
    align-items: center;
    gap: var(--cds-spacing-03);
  }

  .editor {
    flex: 1;
    min-block-size: 0;
  }

  /* The panel gives the border: the editor has none of its own. */
  .editor :global(.code-editor) {
    border: 0;
  }

  .status-count {
    display: inline-flex;
    gap: var(--cds-spacing-02);
    align-items: center;
    font-variant-numeric: tabular-nums;
  }

  /* A count of 0 has the status bar text color; only a problem gets the support color. */
  .status-count :global(svg) {
    fill: var(--cds-icon-secondary);
  }

  .status-count--error :global(svg) {
    fill: var(--cds-support-error);
  }

  .status-count--warning :global(svg) {
    fill: var(--cds-support-warning);
  }

  .new-strategy-form {
    margin-block-end: var(--cds-spacing-05);
  }
</style>
