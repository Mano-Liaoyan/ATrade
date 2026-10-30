<!-- The "Prompt" dialog of the assistant side column (docs/architecture/assistant.md 25.9.2): the version Select, the
     text area of the editable part, the fixed part (read-only), "Restore default", and "Save as new version". A new
     prompt version applies only to new conversations. The logic is in prompt_dialog.ts. The text area and the fixed
     part each scroll in their own ScrollRegion, so each has a visible track when it overflows. -->
<script lang="ts">
  import { Button, Dialog, InlineNotification, Select, type NotificationMessage } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import {
    addSavedVersion,
    describeSaveProblem,
    listPromptVersions,
    openPromptDialog,
    restoreDefault,
    savePromptVersion,
    selectPromptVersion,
    type PromptDialogState,
    type PromptVersion,
  } from './prompt_dialog';

  interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    // Called after a save, for example to show the new version number.
    onSaved?: (version: PromptVersion) => void;
  }

  const { open, onOpenChange, onSaved }: Props = $props();

  const textAreaId = $props.id();
  let dialogState = $state<PromptDialogState | null>(null);
  let problem = $state<NotificationMessage | null>(null);
  let isSaving = $state(false);
  let textArea: HTMLTextAreaElement | undefined = $state();

  // Each open reads the versions again.
  $effect(() => {
    if (!open) {
      return;
    }
    dialogState = null;
    problem = null;
    void listPromptVersions(fetch).then((result) => {
      if (result.kind === 'ok') {
        dialogState = openPromptDialog(result.value);
      } else {
        problem = { kind: 'error', title: 'Prompt versions not read', subtitle: result.message };
      }
    });
  });

  // The text area shows the text of the state and grows with it. The ScrollRegion around it scrolls and draws the
  // track.
  $effect(() => {
    if (textArea === undefined || dialogState === null) {
      return;
    }
    if (textArea.value !== dialogState.text) {
      textArea.value = dialogState.text;
    }
    textArea.style.height = 'auto';
    textArea.style.height = `${String(textArea.scrollHeight)}px`;
  });

  async function saveVersion(): Promise<void> {
    if (dialogState === null) {
      return;
    }
    const saveProblem = describeSaveProblem(dialogState);
    if (saveProblem !== null) {
      problem = { kind: 'error', title: 'Prompt version not saved', subtitle: saveProblem };
      return;
    }
    isSaving = true;
    problem = null;
    const result = await savePromptVersion(fetch, dialogState.text);
    isSaving = false;
    if (result.kind === 'failed') {
      problem = { kind: 'error', title: 'Prompt version not saved', subtitle: result.message };
      return;
    }
    dialogState = addSavedVersion(dialogState, result.value);
    onSaved?.(result.value);
  }
</script>

<Dialog {open} {onOpenChange} title="Prompt" size="lg" busy={isSaving}>
  {#if dialogState !== null}
    {@const currentState = dialogState}
    <div class="prompt-form">
      <Select
        label="Version"
        items={currentState.versionItems}
        value={currentState.selectedVersionId}
        onValueChange={(versionId: string) => {
          dialogState = selectPromptVersion(currentState, versionId);
        }}
      />
      <div class="cds--text-area__wrapper">
        <label for={textAreaId} class="cds--label">Editable part</label>
        <ScrollRegion label="Editable part" maxHeight="20rem">
          <textarea
            id={textAreaId}
            class="cds--text-area prompt-text"
            rows="4"
            bind:this={textArea}
            oninput={(event) => {
              dialogState = { ...currentState, text: event.currentTarget.value };
            }}
          ></textarea>
        </ScrollRegion>
      </div>
      <div>
        <p class="cds--label">Fixed part</p>
        <ScrollRegion label="Fixed part" maxHeight="10rem">
          <pre class="fixed-part">{currentState.fixedPart}</pre>
        </ScrollRegion>
      </div>
      <div class="cds--btn-set">
        <Button kind="secondary" disabled={isSaving} onclick={() => (dialogState = restoreDefault(currentState))}>
          Restore default
        </Button>
        <Button disabled={isSaving} onclick={() => void saveVersion()}>
          {isSaving ? 'Saving…' : 'Save as new version'}
        </Button>
      </div>
    </div>
  {/if}
  {#if problem !== null}
    <InlineNotification {...problem} lowContrast onClose={() => (problem = null)} />
  {/if}
</Dialog>

<style>
  .prompt-form {
    display: grid;
    gap: var(--cds-spacing-05);
    margin-block-end: var(--cds-spacing-05);
  }

  /* The ScrollRegion scrolls the text area, so the text area itself never scrolls. */
  .prompt-text {
    inline-size: 100%;
    overflow: hidden;
    resize: none;
  }

  .fixed-part {
    margin: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
    background: var(--cds-layer-01);
    color: var(--cds-text-secondary);
    font-family: var(--cds-code-01-font-family);
    font-size: var(--cds-code-01-font-size);
    line-height: var(--cds-code-01-line-height);
    white-space: pre-wrap;
  }
</style>
