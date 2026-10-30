<!-- The "AI assistant" side column of the strategy page (docs/architecture/assistant.md 25.12). Default width 28rem,
     with the splitter, Minimize (a 32px rail with the assistant icon), and Maximize.
     Header line: "Credentials" and "Prompt" open their dialogs. Top: the conversation Select of the open strategy,
     "New conversation", "Rename conversation", "Delete conversation" (a danger Dialog first), and the prompt version of
     the open conversation. Middle: the conversation log. Bottom: the provider, model, and credential Selects, the
     message input, and "Send", which becomes "Stop" (abort) while the AI assistant runs. The page gets the errors of
     the conversation for its Output tab, for example a title that was not generated. -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import AiAgent16 from '@carbon/icons/es/ai-agent/16.js';
  import Edit16 from '@carbon/icons/es/edit/16.js';
  import Password16 from '@carbon/icons/es/password/16.js';
  import Script16 from '@carbon/icons/es/script/16.js';
  import TrashCan16 from '@carbon/icons/es/trash-can/16.js';
  import { untrack } from 'svelte';
  import { SvelteMap } from 'svelte/reactivity';
  import {
    addServerMessage,
    addUserMessage,
    changeProvider,
    createConversation,
    CredentialsDialog,
    deleteConversation,
    describeSendButton,
    discardStrategyVersion,
    EMPTY_LOG,
    findDefaultSelection,
    listConversations,
    listCredentials,
    listProviders,
    listSelectItems,
    openConversationSocket,
    PromptDialog,
    readConversation,
    readConversationLog,
    renameConversation,
    type ConnectionState,
    type Conversation,
    type ConversationLog,
    type ConversationSocket,
    type Credential,
    type DiffItem,
    type LastModel,
    type ModelSelection,
    type Provider,
  } from '#lib/assistant';
  import { Button, Dialog, IconButton, Select, TextInput } from '#lib/foundation/carbon';
  import { SideColumn } from '#lib/foundation/workbench';
  import AssistantLog, { type DiffChoice } from './AssistantLog.svelte';

  interface Props {
    strategyId: number;
    /** The version that the editor shows. A new conversation records it (25.9). */
    openVersionNumber: number | null;
    onOpenDiff: (versionNumber: number) => void;
    onKeep: (versionNumber: number) => void;
    onDiscarded: (versionNumber: number) => void;
    onError: (text: string) => void;
    onMaximizedChange: (isMaximized: boolean) => void;
  }

  const { strategyId, openVersionNumber, onOpenDiff, onKeep, onDiscarded, onError, onMaximizedChange }: Props =
    $props();

  // The title is generated after the run settles (25.8.3), so the list is read again a little later.
  const TITLE_READ_DELAY_MILLISECONDS = 1000;
  // The backend refuses a longer title.
  const MAX_TITLE_LENGTH = 200;

  let conversations: Conversation[] = $state([]);
  let conversationId = $state<number | null>(null);
  let log = $state<ConversationLog>(EMPTY_LOG);
  let connection = $state<ConnectionState>('connecting');
  let socket: ConversationSocket | null = null;
  let providers: Provider[] = $state([]);
  let credentials: Credential[] = $state([]);
  let selection = $state<ModelSelection>({ provider: '', model: '', credentialId: '' });
  let text = $state('');
  const diffChoices = new SvelteMap<number, DiffChoice>();
  let isCredentialsOpen = $state(false);
  let isPromptOpen = $state(false);
  let isRenameOpen = $state(false);
  let renameTitle = $state('');
  let isDeleteOpen = $state(false);
  let isDeleting = $state(false);

  const conversation = $derived(conversations.find((item) => item.id === conversationId) ?? null);
  const items = $derived(listSelectItems(providers, credentials, selection.provider));
  const sendButton = $derived(
    describeSendButton({
      hasConversation: conversation !== null,
      hasCredential: selection.credentialId !== '',
      connection,
      isRunning: log.isRunning,
    }),
  );

  async function readConversations(selectId: number | null): Promise<void> {
    const readStrategyId = strategyId;
    const result = await listConversations(fetch, readStrategyId);
    // An answer for a strategy that is not open any more does not change the column.
    if (readStrategyId !== strategyId) {
      return;
    }
    if (result.kind === 'failed') {
      onError(`Conversations not read: ${result.message}`);
      return;
    }
    conversations = result.value;
    const kept = result.value.find((item) => item.id === selectId);
    conversationId = kept?.id ?? result.value[0]?.id ?? null;
  }

  async function readModels(): Promise<void> {
    const [providerResult, credentialResult] = await Promise.all([listProviders(fetch), listCredentials(fetch)]);
    if (providerResult.kind === 'failed') {
      onError(`Providers not read: ${providerResult.message}`);
      return;
    }
    if (credentialResult.kind === 'failed') {
      onError(`Credentials not read: ${credentialResult.message}`);
      return;
    }
    providers = providerResult.value.providers;
    credentials = credentialResult.value.credentials;
    if (!credentials.some((item) => item.id === selection.credentialId)) {
      selection = findDefaultSelection(providers, credentials, readLastModel(conversation));
    }
  }

  function readLastModel(item: Conversation | null): LastModel {
    return {
      provider: item?.last_provider ?? null,
      model: item?.last_model ?? null,
      credentialName: item?.last_credential_name ?? null,
    };
  }

  $effect(() => {
    strategyId satisfies number;
    void readConversations(null);
  });

  $effect(() => {
    void readModels();
  });

  // One socket for the open conversation. A change of the conversation closes it.
  $effect(() => {
    const id = conversationId;
    log = EMPTY_LOG;
    untrack(() => {
      diffChoices.clear();
    });
    if (id === null) {
      return;
    }
    let isCurrent = true;
    let titleTimer: ReturnType<typeof setTimeout> | undefined;
    connection = 'connecting';
    void readConversation(fetch, id).then((result) => {
      if (!isCurrent) {
        return;
      }
      if (result.kind === 'failed') {
        onError(`Conversation not read: ${result.message}`);
        return;
      }
      log = readConversationLog(result.value.messages, result.value.created_at_utc);
      selection = findDefaultSelection(providers, credentials, readLastModel(result.value));
    });
    const opened = openConversationSocket(id, window.location, {
      onMessage: (message) => {
        log = addServerMessage(log, message, new Date().toISOString());
        if (message.type === 'run_state' && message.state === 'settled') {
          clearTimeout(titleTimer);
          titleTimer = setTimeout(() => void readConversations(id), TITLE_READ_DELAY_MILLISECONDS);
        }
      },
      onError,
      onConnectionChange: (connected) => {
        connection = connected ? 'open' : 'closed';
      },
    });
    socket = opened;
    return () => {
      isCurrent = false;
      clearTimeout(titleTimer);
      opened.close();
      socket = null;
    };
  });

  function send(): void {
    const message = text.trim();
    if (sendButton.disabledReason !== null || message === '' || socket === null) {
      return;
    }
    socket.send({
      type: 'prompt',
      text: message,
      provider: selection.provider,
      model: selection.model,
      credential_id: selection.credentialId,
    });
    log = addUserMessage(log, message, new Date().toISOString());
    text = '';
  }

  function pressSendButton(): void {
    if (sendButton.action === 'stop') {
      socket?.send({ type: 'abort' });
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

  async function startConversation(): Promise<void> {
    const result = await createConversation(fetch, strategyId, openVersionNumber);
    if (result.kind === 'failed') {
      onError(`Conversation not created: ${result.message}`);
      return;
    }
    await readConversations(result.value.id);
  }

  async function submitRename(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    if (conversation === null) {
      return;
    }
    const result = await renameConversation(fetch, conversation.id, renameTitle);
    isRenameOpen = false;
    if (result.kind === 'failed') {
      onError(`Conversation not renamed: ${result.message}`);
      return;
    }
    await readConversations(conversation.id);
  }

  async function removeConversation(): Promise<void> {
    if (conversation === null) {
      return;
    }
    isDeleting = true;
    const error = await deleteConversation(fetch, conversation.id);
    isDeleting = false;
    isDeleteOpen = false;
    if (error !== null) {
      onError(`Conversation not deleted: ${error}`);
      return;
    }
    await readConversations(null);
  }

  async function discard(item: DiffItem): Promise<void> {
    const error = await discardStrategyVersion(fetch, item.strategyId, item.versionNumber);
    if (error !== null) {
      onError(`v${String(item.versionNumber)} not discarded: ${error}`);
      return;
    }
    diffChoices.set(item.id, 'discarded');
    onDiscarded(item.versionNumber);
  }
</script>

<SideColumn
  label="AI assistant"
  buttonName="AI assistant"
  side="end"
  width="28rem"
  storageKey="atrade.strategy-page.assistant-column"
  railIcon={AiAgent16}
  maximizable
  {onMaximizedChange}
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
        items={conversations.map((item) => ({ value: String(item.id), label: item.title }))}
        value={conversationId === null ? '' : String(conversationId)}
        placeholder="No conversation"
        disabled={conversations.length === 0}
        onValueChange={(value: string) => {
          conversationId = Number(value);
        }}
      />
    </div>
    <IconButton label="New conversation" icon={Add16} onclick={() => void startConversation()} />
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

  <AssistantLog
    items={log.items}
    isRunning={log.isRunning}
    {diffChoices}
    onOpenDiff={(item: DiffItem) => {
      onOpenDiff(item.versionNumber);
    }}
    onKeep={(item: DiffItem) => {
      diffChoices.set(item.id, 'kept');
      onKeep(item.versionNumber);
    }}
    onDiscard={(item: DiffItem) => void discard(item)}
  />

  <div class="assistant-bottom">
    <div class="model-selects">
      <Select
        label="Provider"
        hideLabel
        size="sm"
        items={items.providers}
        value={selection.provider}
        placeholder="No credential"
        disabled={items.providers.length === 0}
        onValueChange={(value: string) => {
          selection = changeProvider(providers, credentials, value);
        }}
      />
      <Select
        label="Model"
        hideLabel
        size="sm"
        items={items.models}
        value={selection.model}
        placeholder="No model"
        disabled={items.models.length === 0}
        onValueChange={(value: string) => {
          selection = { ...selection, model: value };
        }}
      />
      <Select
        label="Credential"
        hideLabel
        size="sm"
        items={items.credentials}
        value={selection.credentialId}
        placeholder="No credential"
        disabled={items.credentials.length === 0}
        onValueChange={(value: string) => {
          selection = { ...selection, credentialId: value };
        }}
      />
    </div>
    <div class="message-row">
      <textarea
        class="cds--text-area message-input"
        aria-label="Message"
        rows="2"
        bind:value={text}
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
      void readModels();
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

  .model-selects {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--cds-spacing-02);
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
