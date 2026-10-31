<!-- The "AI assistant" side column of each workbench page (docs/architecture/assistant.md 25.12). Default width 28rem,
     with the splitter, Minimize (a 32px rail with the assistant icon), and Maximize. All pages share one state
     (assistant_session.svelte.ts) and one storage key, so a page change keeps the open conversation and Minimize.
     Header line: "Credentials" and "Prompt" open their dialogs. Top: the conversation Select (all conversations),
     "New conversation", "Rename conversation", "Delete conversation" (a danger Dialog first), and the prompt version of
     the open conversation. Middle: the conversation log. Bottom: the Model (wide, for the full name) and Thinking Selects,
     the Provider and Credential Selects, the message input, and "Send", which becomes "Stop" (abort) while the AI
     assistant runs.
     The strategy page gives its open strategy, its diff card actions, and its Output tab for the errors. A page
     without an Output tab shows the last error in the column. A diff card of another strategy, or on another page,
     opens the strategy page: the card opens the diff there, and Keep opens the version. -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import AiAgent16 from '@carbon/icons/es/ai-agent/16.js';
  import Edit16 from '@carbon/icons/es/edit/16.js';
  import Password16 from '@carbon/icons/es/password/16.js';
  import Script16 from '@carbon/icons/es/script/16.js';
  import TrashCan16 from '@carbon/icons/es/trash-can/16.js';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { untrack } from 'svelte';
  import {
    changeProvider,
    CredentialsDialog,
    describeSendButton,
    listSelectItems,
    PromptDialog,
    type DiffItem,
    type ThinkingLevel,
  } from '#lib/assistant';
  import { Button, Dialog, IconButton, InlineNotification, Select, TextInput } from '#lib/foundation/carbon';
  import { SideColumn } from '#lib/foundation/workbench';
  import AssistantLog from './AssistantLog.svelte';
  import { assistantSession as session, type OpenStrategy } from './assistant_session.svelte';

  interface Props {
    /** The open strategy and version of the page. Null on a page without an open strategy. */
    openStrategy?: OpenStrategy | null;
    /** The diff card actions of the strategy page, for a card of its open strategy. */
    onOpenDiff?: (versionNumber: number) => void;
    onKeep?: (versionNumber: number) => void;
    onDiscarded?: (versionNumber: number) => void;
    /** The Output tab of the page. Without it, the column shows the last error. */
    onError?: (text: string) => void;
  }

  const { openStrategy = null, onOpenDiff, onKeep, onDiscarded, onError }: Props = $props();

  // The backend refuses a longer title.
  const MAX_TITLE_LENGTH = 200;

  let isCredentialsOpen = $state(false);
  let isPromptOpen = $state(false);
  let isRenameOpen = $state(false);
  let renameTitle = $state('');
  let isDeleteOpen = $state(false);
  let isDeleting = $state(false);

  const conversation = $derived(session.conversation);
  const log = $derived(session.log);
  const items = $derived(listSelectItems(session.providers, session.credentials, session.selection.provider));
  const sendButton = $derived(
    describeSendButton({
      hasConversation: conversation !== null,
      hasCredential: session.selection.credentialId !== '',
      connection: session.connection,
      isRunning: log.isRunning,
    }),
  );

  $effect(() => {
    if (onError === undefined) {
      return;
    }
    return session.receiveErrors(onError);
  });

  // Each page reads the list again: another page or a strategy delete can have changed it.
  $effect(() => {
    untrack(() => {
      void session.readConversations();
      void session.readModels();
    });
  });

  function isOpenStrategy(item: DiffItem): boolean {
    return openStrategy?.strategyId === item.strategyId;
  }

  function openStrategyVersion(item: DiffItem): void {
    void goto(
      resolve('/strategies/[strategyId]/versions/[versionNumber]', {
        strategyId: String(item.strategyId),
        versionNumber: String(item.versionNumber),
      }),
    );
  }

  function openDiff(item: DiffItem): void {
    if (isOpenStrategy(item) && onOpenDiff !== undefined) {
      onOpenDiff(item.versionNumber);
      return;
    }
    session.requestDiff({ strategyId: item.strategyId, versionNumber: item.versionNumber });
    void goto(resolve('/strategies/[strategyId]', { strategyId: String(item.strategyId) }));
  }

  function keep(item: DiffItem): void {
    session.diffChoices.set(item.id, 'kept');
    if (isOpenStrategy(item) && onKeep !== undefined) {
      onKeep(item.versionNumber);
      return;
    }
    openStrategyVersion(item);
  }

  async function discard(item: DiffItem): Promise<void> {
    if ((await session.discard(item)) && isOpenStrategy(item)) {
      onDiscarded?.(item.versionNumber);
    }
  }

  function send(): void {
    if (sendButton.disabledReason === null) {
      session.send();
    }
  }

  function pressSendButton(): void {
    if (sendButton.action === 'stop') {
      session.abort();
      return;
    }
    send();
  }

  function sendOnEnter(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      if (!log.isRunning) {
        send();
      }
    }
  }

  async function submitRename(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    if (conversation === null) {
      return;
    }
    const id = conversation.id;
    isRenameOpen = false;
    await session.rename(id, renameTitle);
  }

  async function removeConversation(): Promise<void> {
    if (conversation === null) {
      return;
    }
    isDeleting = true;
    await session.delete(conversation.id);
    isDeleting = false;
    isDeleteOpen = false;
  }
</script>

<SideColumn
  label="AI assistant"
  buttonName="AI assistant"
  side="end"
  width="28rem"
  storageKey="atrade.assistant-column"
  railIcon={AiAgent16}
  maximizable
>
  {#snippet actions()}
    <IconButton label="Credentials" icon={Password16} onclick={() => (isCredentialsOpen = true)} />
    <IconButton label="Prompt" icon={Script16} onclick={() => (isPromptOpen = true)} />
  {/snippet}
  <div class="assistant-top">
    <div class="conversation-select">
      <Select
        label="Conversation"
        hideLabel
        size="sm"
        items={session.conversations.map((item) => ({ value: String(item.id), label: item.title }))}
        value={session.conversationId === null ? '' : String(session.conversationId)}
        placeholder="No conversation"
        disabled={session.conversations.length === 0}
        onValueChange={(value: string) => {
          session.openConversation(Number(value));
        }}
      />
    </div>
    <IconButton label="New conversation" icon={Add16} onclick={() => void session.startConversation(openStrategy)} />
    <IconButton
      label={conversation === null ? 'No conversation to rename' : 'Rename conversation'}
      icon={Edit16}
      disabled={conversation === null}
      onclick={() => {
        renameTitle = conversation?.title ?? '';
        isRenameOpen = true;
      }}
    />
    <IconButton
      label={conversation === null ? 'No conversation to delete' : 'Delete conversation'}
      icon={TrashCan16}
      disabled={conversation === null}
      align="bottom-end"
      onclick={() => (isDeleteOpen = true)}
    />
    {#if conversation !== null}
      <span class="prompt-version">Prompt v{conversation.prompt_version_number}</span>
    {/if}
  </div>

  {#if onError === undefined && session.errorText !== ''}
    <div class="assistant-error">
      <InlineNotification
        kind="error"
        title={session.errorText}
        lowContrast
        onClose={() => {
          session.errorText = '';
        }}
      />
    </div>
  {/if}

  <AssistantLog
    items={log.items}
    isRunning={log.isRunning}
    diffChoices={session.diffChoices}
    onOpenDiff={openDiff}
    onKeep={keep}
    onDiscard={(item: DiffItem) => void discard(item)}
    screenChoices={session.screenChoices}
    onKeepScreen={(screenId: number) => void session.keepScreen(screenId)}
    onDiscardScreen={(screenId: number) => void session.discardScreen(screenId)}
  />

  <div class="assistant-bottom">
    <div class="model-row">
      <Select
        label="Model"
        hideLabel
        size="sm"
        items={items.models}
        value={session.selection.model}
        placeholder="No model"
        disabled={items.models.length === 0}
        onValueChange={(value: string) => {
          session.selection = { ...session.selection, model: value };
        }}
      />
      <Select
        label="Thinking"
        hideLabel
        size="sm"
        items={session.thinking.items}
        value={session.thinking.value}
        placeholder="No thinking"
        disabled={session.thinking.disabledReason !== null}
        disabledReason={session.thinking.disabledReason}
        onValueChange={(value: ThinkingLevel) => {
          session.chooseThinkingLevel(value);
        }}
      />
    </div>
    <div class="credential-row">
      <Select
        label="Provider"
        hideLabel
        size="sm"
        items={items.providers}
        value={session.selection.provider}
        placeholder="No credential"
        disabled={items.providers.length === 0}
        onValueChange={(value: string) => {
          session.selection = changeProvider(session.providers, session.credentials, value);
        }}
      />
      <Select
        label="Credential"
        hideLabel
        size="sm"
        items={items.credentials}
        value={session.selection.credentialId}
        placeholder="No credential"
        disabled={items.credentials.length === 0}
        onValueChange={(value: string) => {
          session.selection = { ...session.selection, credentialId: value };
        }}
      />
    </div>
    <div class="message-row">
      <textarea
        class="cds--text-area message-input"
        aria-label="Message"
        rows="2"
        bind:value={session.text}
        onkeydown={sendOnEnter}
      ></textarea>
      <Button
        kind={sendButton.action === 'stop' ? 'danger' : 'primary'}
        size="md"
        disabled={sendButton.disabledReason !== null}
        aria-describedby={sendButton.disabledReason === null ? undefined : 'assistant-send-reason'}
        onclick={pressSendButton}>{sendButton.label}</Button
      >
    </div>
    {#if sendButton.disabledReason !== null}
      <p id="assistant-send-reason" class="cds--form__helper-text">{sendButton.disabledReason}</p>
    {/if}
  </div>
</SideColumn>

<CredentialsDialog
  open={isCredentialsOpen}
  onOpenChange={(open: boolean) => {
    isCredentialsOpen = open;
    if (!open) {
      void session.readModels();
    }
  }}
/>

<PromptDialog
  open={isPromptOpen}
  onOpenChange={(open: boolean) => {
    isPromptOpen = open;
  }}
/>

{#if conversation !== null}
  <Dialog
    open={isRenameOpen}
    onOpenChange={(open: boolean) => {
      isRenameOpen = open;
    }}
    title="Rename conversation"
    primaryText="Rename conversation"
    onPrimary={() => {
      document.querySelector<HTMLFormElement>('#rename-conversation-form')?.requestSubmit();
    }}
  >
    <form id="rename-conversation-form" class="rename-form" aria-label="Rename conversation" onsubmit={submitRename}>
      <TextInput label="Title" name="title" bind:value={renameTitle} required maxlength={MAX_TITLE_LENGTH} />
    </form>
  </Dialog>

  <Dialog
    open={isDeleteOpen}
    onOpenChange={(open: boolean) => {
      isDeleteOpen = open;
    }}
    title="Delete {conversation.title}"
    primaryText="Delete conversation"
    primaryKind="danger"
    busy={isDeleting}
    onPrimary={() => void removeConversation()}
  >
    <p>The messages of the conversation are deleted. Its strategy versions and backtests stay.</p>
  </Dialog>
{/if}

<style>
  .assistant-top {
    display: flex;
    flex: none;
    align-items: center;
    gap: var(--cds-spacing-02);
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .assistant-error {
    flex: none;
  }

  .assistant-error :global(.cds--inline-notification) {
    max-inline-size: none;
    margin-block: 0;
  }

  .conversation-select {
    flex: 1;
    min-inline-size: 0;
  }

  .prompt-version {
    flex: none;
    color: var(--cds-text-secondary);
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
    white-space: nowrap;
  }

  .assistant-bottom {
    display: flex;
    flex: none;
    flex-direction: column;
    gap: var(--cds-spacing-03);
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
    border-block-start: 1px solid var(--cds-border-subtle-01);
  }

  /* The Model field takes 2 parts, so a long model name has room. */
  .model-row,
  .credential-row {
    display: grid;
    gap: var(--cds-spacing-02);
  }

  .model-row {
    grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  }

  .credential-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .message-row {
    display: flex;
    align-items: flex-end;
    gap: var(--cds-spacing-03);
  }

  .message-input {
    flex: 1;
    min-inline-size: 0;
    resize: none;
  }

  .rename-form {
    margin-block-end: var(--cds-spacing-05);
  }
</style>
