<!-- Strategy page: a workbench (foundation/workbench, spec #99, ticket #106) like the QuantConnect editor. URL:
     /strategies/<id>; /strategies opens the first strategy of the list.
     Left: the "Strategies" side column with the "New strategy" button. Center: the toolbar line (strategy name, version,
     and icon buttons with the state in their icon and color), then the results panel and the editor panel with a
     splitter between them. The swap button puts the editor on top or at the bottom; the browser keeps the choice.
     The results panel has one tab for each backtest of the strategy (number and total return), then Trades, Orders,
     and Logs. A backtest that ends opens in its tab. The editor panel has the file tab and the code editor. Unsaved
     edits stay in localStorage (drafts of the strategy capability). -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import ArrowDown16 from '@carbon/icons/es/arrow--down/16.js';
  import ArrowUp16 from '@carbon/icons/es/arrow--up/16.js';
  import ConnectionSignal16 from '@carbon/icons/es/connection-signal/16.js';
  import InProgress16 from '@carbon/icons/es/in-progress/16.js';
  import PlayFilledAlt16 from '@carbon/icons/es/play--filled--alt/16.js';
  import Save16 from '@carbon/icons/es/save/16.js';
  import StopFilledAlt16 from '@carbon/icons/es/stop--filled--alt/16.js';
  import TrashCan16 from '@carbon/icons/es/trash-can/16.js';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { isFinalStatus, listBacktests, type Backtest } from '#lib/backtest';
  import {
    Dialog,
    IconButton,
    InlineNotification,
    Select,
    TextInput,
    type NotificationMessage,
  } from '#lib/foundation/carbon';
  import { CodeEditor } from '#lib/foundation/code_editor';
  import { LiveUpdatesNotification } from '#lib/foundation/live_socket';
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
  } from '#lib/strategy';
  import StartBacktestDialog from '../backtests/StartBacktestDialog.svelte';
  import StartForwardTestDialog from './StartForwardTestDialog.svelte';
  import StrategyList from './StrategyList.svelte';
  import StrategyResults from './StrategyResults.svelte';
  import {
    createBacktestTab,
    describeShortcut,
    describeSwapButton,
    findFinishedBacktest,
    isMacPlatform,
    listResultTabs,
    listWorkbenchPanels,
    PANE_ORDER_STORAGE_KEY,
    readPaneOrder,
    readWorkbenchShortcut,
    resolveResultTab,
    selectStrategyBacktests,
    swapPaneOrder,
    type PaneOrder,
    type ResultSelection,
    type ResultTab,
    type WorkbenchShortcut,
  } from './strategy_workbench';

  const { strategyId }: { strategyId: number | null } = $props();

  // The backend refuses a longer name.
  const STRATEGY_NAME_MAX_LENGTH = 100;
  const LIST_CHECK_INTERVAL_MILLISECONDS = 2000;
  const FILE_TABS = [{ value: 'strategy', label: 'strategy.py' }];
  const isMac = isMacPlatform(navigator);

  let strategies: StrategyListItem[] = $state([]);
  let listMessage = $state('');
  // A new value reads the strategy list again, for example after a save.
  let listReadCount = $state(0);
  let strategy = $state<StrategyDetail | null>(null);
  let openVersion = $state<StrategyVersion | null>(null);
  let editorCode = $state('');
  let problems: CodeProblem[] = $state([]);
  let saveMessage = $state<NotificationMessage | null>(null);
  let isSaving = $state(false);
  let backtests: Backtest[] = $state([]);
  // A new value reads the backtest list again, for example after a new backtest starts.
  let backtestReadCount = $state(0);
  let selection = $state<ResultSelection>({ tab: null, backtestId: null });
  let paneOrder = $state<PaneOrder>(readPaneOrder(readStoredLayout(PANE_ORDER_STORAGE_KEY)));
  let forwardTestMessage = $state<NotificationMessage | null>(null);
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
  const runningForwardTest = $derived(
    forwardTestFeed.forwardTests
      .filter((forwardTest) => forwardTest.strategy_id === activeStrategyId && forwardTest.desired_state === 'running')
      .reduce<{ id: number } | null>((newest, forwardTest) => (newest === null || forwardTest.id > newest.id ? forwardTest : newest), null),
  );
  const hasUnsavedChanges = $derived(openVersion !== null && editorCode !== openVersion.code);
  const versionItems = $derived(
    (strategy?.versions ?? []).map((version) => ({
      value: String(version.version_number),
      label: `v${String(version.version_number)}`,
    })),
  );
  const openVersionLabel = $derived(
    strategy === null || openVersion === null ? '' : formatVersionLabel(strategy.name, openVersion.version_number),
  );
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
    const readNumber = backtestReadCount;
    let isActive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function readList(): Promise<void> {
      const result = await listBacktests(fetch);
      if (!isActive || readNumber !== backtestReadCount || result.kind === 'failed') {
        return;
      }
      const finished = findFinishedBacktest(backtests, result.value, activeStrategyId);
      if (finished !== null) {
        selection = { tab: createBacktestTab(finished.id), backtestId: finished.id };
      }
      backtests = result.value;
      if (result.value.some((item) => !isFinalStatus(item.status))) {
        timer = setTimeout(() => void readList(), LIST_CHECK_INTERVAL_MILLISECONDS);
      }
    }

    void readList();
    return () => {
      isActive = false;
      clearTimeout(timer);
    };
  });

  $effect(() => {
    const id = activeStrategyId;
    strategy = null;
    openVersion = null;
    problems = [];
    saveMessage = null;
    selection = { tab: null, backtestId: null };
    if (id !== null) {
      void loadStrategy(id, null);
    }
  });

  async function loadStrategy(id: number, versionNumberToOpen: number | null): Promise<void> {
    const result = await readStrategy(fetch, id);
    if (result.kind === 'failed') {
      saveMessage = { kind: 'error', title: 'Strategy not read', subtitle: result.message };
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
      saveMessage = { kind: 'error', title: 'Version not read', subtitle: result.message };
      return;
    }
    const draft = readDraft(localStorage, { strategyId: id, versionNumber });
    openVersion = result.value;
    editorCode = draft ?? result.value.code;
    problems = [];
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
    saveMessage = null;
    problems = [];
    if (result.kind === 'check_failed') {
      problems = result.problems;
      return;
    }
    if (result.kind === 'failed') {
      saveMessage = { kind: 'error', title: 'Version not saved', subtitle: result.message };
      return;
    }
    clearDraft(localStorage, { strategyId: id, versionNumber: baseVersionNumber });
    const label = formatVersionLabel(name, result.version.version_number);
    await loadStrategy(id, result.version.version_number);
    listReadCount += 1;
    saveMessage = {
      kind: 'success',
      title: result.isNewVersion ? `Saved as ${label}.` : `Saved. The code is the same as ${label}.`,
    };
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
    forwardTestMessage = null;
    const forwardTestId = runningForwardTest.id;
    const result = await stopForwardTest(fetch, forwardTestId);
    isStoppingForwardTest = false;
    if (result.kind === 'failed') {
      forwardTestMessage = { kind: 'error', title: 'Forward test not stopped', subtitle: result.message };
      return;
    }
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
    const backtestTab = resultTabs.find((item) => item.value === tab && item.value.startsWith('backtest-'));
    selection = {
      tab,
      backtestId: backtestTab === undefined ? shownResult.backtestId : Number(tab.slice('backtest-'.length)),
    };
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
      saveMessage = { kind: 'error', title: 'Strategy not deleted', subtitle: result.message };
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

  <div class="main">
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
              saveMessage = null;
              void openStrategyVersion(shownStrategy.id, Number(versionNumber));
            }}
          />
        </div>
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
      {#if forwardTestMessage !== null}
        <InlineNotification {...forwardTestMessage} lowContrast onClose={() => (forwardTestMessage = null)} />
      {/if}

      <PanelSplit storageKey="atrade.strategy-page.panel-split" {panels}>
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
          {:else}
            <Panel
              {...state}
              label="Editor"
              tabs={{ label: 'Files', items: FILE_TABS, value: 'strategy', onValueChange: () => {} }}
            >
              {#if saveMessage !== null}
                <InlineNotification {...saveMessage} lowContrast onClose={() => (saveMessage = null)} />
              {/if}
              {#if problems.length > 0}
                <InlineNotification kind="error" lowContrast title="The code was not saved. Fix these problems:">
                  <ul class="problem-list">
                    {#each problems as problem, index (index)}
                      <li>Line {problem.line}: {problem.message}</li>
                    {/each}
                  </ul>
                </InlineNotification>
              {/if}
              {#if openVersion !== null}
                <div class="editor">
                  {#key shownStrategy.id}
                    <CodeEditor
                      code={editorCode}
                      label="Strategy code"
                      onCodeChange={changeCode}
                      extensions={[languageServer.editorExtension]}
                    />
                  {/key}
                </div>
              {/if}
            </Panel>
          {/if}
        {/snippet}
      </PanelSplit>
    {:else if strategies.length === 0 && listMessage === '' && strategyId === null}
      <p class="empty-word">No strategies</p>
    {/if}
  </div>
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
  strategyVersion={openVersion === null ? null : { strategyId: openVersion.strategy_id, versionId: openVersion.id }}
  onStarted={() => {
    backtestReadCount += 1;
  }}
/>

<StartForwardTestDialog
  open={isForwardTestDialogOpen}
  title={`Start forward test of ${openVersionLabel}`}
  strategyVersionId={openVersion?.id ?? null}
  onOpenChange={(open: boolean) => {
    isForwardTestDialogOpen = open;
  }}
  onStarted={(forwardTest: ForwardTest) => {
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

  .strategy-name {
    flex: 0 1 auto;
    min-inline-size: 0;
  }

  .version-select {
    flex: none;
    inline-size: var(--cds-spacing-11);
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

  .problem-list {
    margin-block: var(--cds-spacing-02) 0;
    padding-inline-start: var(--cds-spacing-05);
    list-style: disc;
  }

  .new-strategy-form {
    margin-block-end: var(--cds-spacing-05);
  }

  .empty-word {
    margin: 0;
    padding: var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    color: var(--cds-text-secondary);
  }
</style>
