<!-- Strategy editor: open a version, edit its code, and save it as a new version. Unsaved edits stay in localStorage. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
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

  // Code completion and live type errors. Type errors do not block the save.
  const languageServer = connectStrategyLanguageServer(window.location);
  $effect(() => () => {
    languageServer.disconnect();
  });

  const hasUnsavedChanges = $derived(openVersion !== null && editorCode !== openVersion.code);

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

  function selectVersion(event: Event): void {
    const select = event.currentTarget as HTMLSelectElement;
    saveMessage = '';
    void openStrategyVersion(Number(select.value));
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
    if (!window.confirm('Delete this strategy and all its versions?')) {
      return;
    }
    const result = await deleteStrategy(fetch, strategyId);
    if (result.kind === 'failed') {
      errorMessage = result.message;
      return;
    }
    await goto(resolve('/strategies'));
  }
</script>

<p><a href={resolve('/strategies')}>All strategies</a></p>

{#if strategy !== null}
  <h1>{strategy.name}</h1>

  <div class="toolbar">
    <label>
      Version
      <select value={openVersion?.version_number} onchange={selectVersion}>
        {#each strategy.versions as version (version.id)}
          <option value={version.version_number}>{formatVersionLabel(strategy.name, version.version_number)}</option>
        {/each}
      </select>
    </label>
    <button type="button" onclick={saveVersion} disabled={isSaving}>Save version</button>
    {#if hasUnsavedChanges}
      <span class="unsaved">Unsaved changes</span>
    {/if}
    <button type="button" class="delete-button" onclick={removeStrategy}>Delete strategy</button>
  </div>

  {#if saveMessage !== ''}
    <p role="status">{saveMessage}</p>
  {/if}

  {#if problems.length > 0}
    <div class="problems" role="alert">
      <p>The code was not saved. Fix these problems:</p>
      <ul>
        {#each problems as problem, index (index)}
          <li>Line {problem.line}: {problem.message}</li>
        {/each}
      </ul>
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
{/if}

{#if errorMessage !== ''}
  <p class="error" role="alert">{errorMessage}</p>
{/if}

<style>
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
  }

  .unsaved {
    color: var(--color-muted);
    font-style: italic;
  }

  .delete-button {
    margin-left: auto;
  }

  .problems,
  .error {
    color: #cf222e;
  }

  .editor-region {
    height: 65vh;
  }
</style>
