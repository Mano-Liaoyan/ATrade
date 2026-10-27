<!-- Strategy editor: open a version, edit its code, and save it as a new version. Unsaved edits stay in localStorage. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { Button, Dialog, InlineNotification, Select, Tag, type SelectItem } from '#lib/foundation/carbon';
  import { CodeEditor } from '#lib/foundation/code_editor';
  import {
    clearDraft,
    connectStrategyLanguageServer,
    deleteStrategy,
    formatVersionLabel,
    readDraft,
    readStrategy,
    readStrategyVersion,
    saveStrategyVersion,
    writeDraft,
    type CodeProblem,
    type StrategyDetail,
    type StrategyVersion,
  } from '#lib/strategy';

  const strategyId = $derived(Number(page.params['strategyId']));

  let strategy = $state<StrategyDetail | null>(null);
  let openVersion = $state<StrategyVersion | null>(null);
  let editorCode = $state('');
  let problems: CodeProblem[] = $state([]);
  let saveMessage = $state('');
  let errorMessage = $state('');
  let isSaving = $state(false);
  let isDeleteDialogOpen = $state(false);
  let isDeleting = $state(false);

  // Code completion and live type errors. Type errors do not block the save.
  const languageServer = connectStrategyLanguageServer(window.location);
  $effect(() => () => {
    languageServer.disconnect();
  });

  const hasUnsavedChanges = $derived(openVersion !== null && editorCode !== openVersion.code);
  const versionItems: SelectItem<string>[] = $derived.by(() => {
    const strategyName = strategy?.name ?? '';
    return (strategy?.versions ?? []).map((version) => ({
      value: String(version.version_number),
      label: formatVersionLabel(strategyName, version.version_number),
    }));
  });

  $effect(() => {
    void loadStrategy(strategyId, null);
  });

  async function loadStrategy(id: number, versionNumberToOpen: number | null): Promise<void> {
    const result = await readStrategy(fetch, id);
    if (result.kind === 'failed') {
      errorMessage = result.message;
      return;
    }
    strategy = result.value;
    const latestVersion = result.value.versions.at(-1);
    const versionNumber = versionNumberToOpen ?? latestVersion?.version_number;
    if (versionNumber !== undefined) {
      await openStrategyVersion(versionNumber);
    }
  }

  async function openStrategyVersion(versionNumber: number): Promise<void> {
    const result = await readStrategyVersion(fetch, strategyId, versionNumber);
    if (result.kind === 'failed') {
      errorMessage = result.message;
      return;
    }
    const draft = readDraft(localStorage, { strategyId, versionNumber });
    openVersion = result.value;
    editorCode = draft ?? result.value.code;
    problems = [];
  }

  function changeCode(code: string): void {
    editorCode = code;
    if (openVersion === null) {
      return;
    }
    const draftKey = { strategyId, versionNumber: openVersion.version_number };
    if (code === openVersion.code) {
      clearDraft(localStorage, draftKey);
    } else {
      writeDraft(localStorage, draftKey, code);
    }
  }

  function selectVersion(versionNumber: string): void {
    saveMessage = '';
    void openStrategyVersion(Number(versionNumber));
  }

  async function saveVersion(): Promise<void> {
    if (openVersion === null || strategy === null) {
      return;
    }
    const baseVersionNumber = openVersion.version_number;
    isSaving = true;
    const result = await saveStrategyVersion(fetch, strategyId, editorCode);
    isSaving = false;
    saveMessage = '';
    errorMessage = '';
    problems = [];
    if (result.kind === 'check_failed') {
      problems = result.problems;
      return;
    }
    if (result.kind === 'failed') {
      errorMessage = result.message;
      return;
    }
    clearDraft(localStorage, { strategyId, versionNumber: baseVersionNumber });
    const label = formatVersionLabel(strategy.name, result.version.version_number);
    await loadStrategy(strategyId, result.version.version_number);
    saveMessage = result.isNewVersion ? `Saved as ${label}.` : `Saved. The code is the same as ${label}.`;
  }

  async function removeStrategy(): Promise<void> {
    isDeleting = true;
    const result = await deleteStrategy(fetch, strategyId);
    isDeleting = false;
    isDeleteDialogOpen = false;
    if (result.kind === 'failed') {
      errorMessage = result.message;
      return;
    }
    await goto(resolve('/strategies'));
  }
</script>

<p class="back-link"><a class="cds--link" href={resolve('/strategies')}>All strategies</a></p>

{#if strategy !== null}
  <h1>{strategy.name}</h1>

  <div class="toolbar">
    <div class="version-select">
      <Select
        label="Version"
        items={versionItems}
        value={String(openVersion?.version_number ?? '')}
        onValueChange={(versionNumber: string) => {
          selectVersion(versionNumber);
        }}
      />
    </div>
    <Button size="md" onclick={saveVersion} disabled={isSaving}>{isSaving ? 'Saving…' : 'Save version'}</Button>
    {#if hasUnsavedChanges}
      <Tag label="Unsaved changes" kind="warm-gray" />
    {/if}
    <Button
      kind="danger"
      size="md"
      class="delete-button"
      onclick={() => {
        isDeleteDialogOpen = true;
      }}
    >
      Delete strategy
    </Button>
  </div>

  {#if saveMessage !== '' || problems.length > 0}
    <div class="results">
      {#if saveMessage !== ''}
        <InlineNotification
          kind="success"
          lowContrast
          title={saveMessage}
          onClose={() => {
            saveMessage = '';
          }}
        />
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
    </div>
  {/if}

  {#if openVersion !== null}
    <div class="editor-region">
      <CodeEditor
        code={editorCode}
        label="Strategy code"
        onCodeChange={changeCode}
        extensions={[languageServer.editorExtension]}
      />
    </div>
  {/if}

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

{#if errorMessage !== ''}
  <div class="page-error">
    <InlineNotification kind="error" lowContrast title={errorMessage} />
  </div>
{/if}

<style>
  .back-link {
    margin-block: 0 var(--cds-spacing-05);
  }

  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: end;
    gap: var(--cds-spacing-05);
    margin-block-end: var(--cds-spacing-05);
  }

  .version-select {
    inline-size: calc(2 * var(--cds-spacing-13));
  }

  .toolbar :global(.delete-button) {
    margin-inline-start: auto;
  }

  .results {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-03);
    margin-block-end: var(--cds-spacing-05);
  }

  .results :global(.cds--inline-notification) {
    margin-block: 0;
  }

  .page-error {
    margin-block-start: var(--cds-spacing-05);
  }

  .page-error :global(.cds--inline-notification) {
    margin-block: 0;
  }

  .problem-list {
    margin-block: var(--cds-spacing-02) 0;
    padding-inline-start: var(--cds-spacing-05);
    list-style: disc;
  }

  .editor-region {
    height: 65vh;
  }
</style>
