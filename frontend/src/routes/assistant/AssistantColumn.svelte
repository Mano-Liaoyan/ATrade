<!-- The "AI assistant" side column of each workbench page (docs/architecture/assistant.md 25.12). Default width 28rem,
     with the splitter, Minimize (a 32px rail with the assistant icon), and Maximize. All pages share one state
     (assistant_session.svelte.ts) and one storage key, so a page change keeps the open conversation and Minimize.
     Header line: "Credentials" and "Prompt" open their dialogs. The Prompt button tooltip names the prompt version of
     the open conversation, for example "Prompt v3". Top: the conversation Select (all conversations),
     "New conversation", "Rename conversation", and "Delete conversation" (a danger Dialog first). Middle: the
     conversation log. Bottom: the composer, one box with the message input, the inline
     Model (the full name) and Thinking Selects, and the "Send" icon button, which becomes "Stop" (abort) while the AI
     assistant runs. Under the box: the inline Provider and Credential Selects.
     The strategy page gives its open strategy, its diff card actions, and its Output tab for the errors. A page
     without an Output tab shows the last error in the column. A diff card of another strategy, or on another page,
     opens the strategy page: the card opens the diff there, and Keep opens the version. -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import AiAgent16 from '@carbon/icons/es/ai-agent/16.js';
  import Edit16 from '@carbon/icons/es/edit/16.js';
  import Password16 from '@carbon/icons/es/password/16.js';
  import Script16 from '@carbon/icons/es/script/16.js';
  import SendFilled16 from '@carbon/icons/es/send--filled/16.js';
  import StopFilledAlt16 from '@carbon/icons/es/stop--filled--alt/16.js';
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
  import { Dialog, IconButton, InlineNotification, Select, TextInput } from '#lib/foundation/carbon';
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
    <IconButton
      label={conversation === null ? 'Prompt' : `Prompt v${String(conversation.prompt_version_number)}`}
      icon={Script16}
      onclick={() => (isPromptOpen = true)}
    />
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
    <div class="composer" role="group" aria-label="New message">
      <textarea class="message-input" aria-label="Message" rows="2" bind:value={session.text} onkeydown={sendOnEnter}
      ></textarea>
      <div class="composer-bar">
        <div class="model-field">
          <Select
            label="Model"
            hideLabel
            inline
            size="sm"
            items={items.models}
            value={session.selection.model}
            placeholder="No model"
            disabled={items.models.length === 0}
            onValueChange={(value: string) => {
              session.selection = { ...session.selection, model: value };
            }}
          />
        </div>
        <div class="thinking-field">
          <Select
            label="Thinking"
            hideLabel
            inline
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
        <div class="send-button">
          <IconButton
            kind={sendButton.action === 'stop' ? 'danger' : 'primary'}
            label={sendButton.label}
            icon={sendButton.action === 'stop' ? StopFilledAlt16 : SendFilled16}
            align="left"
            disabled={sendButton.disabledReason !== null}
            describedBy={sendButton.disabledReason === null ? undefined : 'assistant-send-reason'}
            onclick={pressSendButton}
          />
        </div>
      </div>
    </div>
    <div class="credential-row">
      <Select
        label="Provider"
        hideLabel
        inline
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
        inline
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

  .assistant-bottom {
    display: flex;
    flex: none;
    flex-direction: column;
    gap: var(--cds-spacing-02);
    padding: var(--cds-spacing-03) var(--cds-spacing-05) var(--cds-spacing-05);
  }

  /* Carbon has no composer. One field box (the Carbon text area look): the message input on top, and a line with the
     inline Model and Thinking Selects and the Send button. The focus outline goes around the whole box. */
  .composer {
    display: flex;
    flex-direction: column;
    border-block-end: 1px solid var(--cds-border-strong-01);
    background: var(--cds-field-01);
  }

  .composer:focus-within {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .message-input {
    box-sizing: border-box;
    inline-size: 100%;
    padding: var(--cds-spacing-04) var(--cds-spacing-05) var(--cds-spacing-02);
    border: 0;
    outline: 0;
    background: transparent;
    color: var(--cds-text-primary);
    font-family: inherit;
    font-size: var(--cds-body-01-font-size);
    line-height: var(--cds-body-01-line-height);
    letter-spacing: var(--cds-body-01-letter-spacing);
    resize: none;
  }

  .message-input::placeholder {
    color: var(--cds-text-placeholder);
  }

  .composer-bar {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-02);
    min-inline-size: 0;
    padding: 0 var(--cds-spacing-02) var(--cds-spacing-02);
  }

  /* The Model field shrinks last: a long name gets the ellipsis, and the Select tooltip gives the full name. */
  .model-field {
    flex: 0 1 auto;
    min-inline-size: 0;
  }

  .thinking-field {
    flex: none;
  }

  .model-field :global(.cds--list-box__wrapper--inline) {
    display: block;
    max-inline-size: 100%;
  }

  .model-field :global(.cds--dropdown--inline) {
    max-inline-size: 100%;
  }

  .send-button {
    flex: none;
    margin-inline-start: auto;
  }

  .credential-row {
    display: flex;
    gap: var(--cds-spacing-02);
    min-inline-size: 0;
  }

  .credential-row > :global(*) {
    flex: 0 1 auto;
    min-inline-size: 0;
  }

  .rename-form {
    margin-block-end: var(--cds-spacing-05);
  }
</style>
