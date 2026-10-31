<!-- The "Credentials" dialog of the AI assistant (docs/architecture/assistant.md 25.7.4). The table lists the credentials:
     name with a status icon before it (the tooltip gives the state and the reason of a failure), provider, and kind (an
     API key shows only its last 4 characters). Below it, a subscription login or an
     API key is added: the dialog starts a login on /ws/assistant and shows each step that pi asks for (the
     authorization link, the device code, a field to paste a code, or a password field for a new API key).
     Closing the dialog closes the socket, and the login stops. #185 puts the icon button in the side column. -->
<script lang="ts">
  import {
    Button,
    ContentSwitcher,
    DataTable,
    Dialog,
    InlineNotification,
    OverflowMenu,
    Select,
    StatusIndicator,
    TextInput,
    type SelectItem,
    type TableColumn,
  } from '#lib/foundation/carbon';
  import { buildSocketUrl } from '#lib/foundation/live_socket';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import {
    addLoginMessage,
    answerPrompt,
    deleteCredential,
    describeCredentialKind,
    describeCredentialState,
    formatKey,
    isLoginWaiting,
    listCredentials,
    listLoginProviders,
    listProviders,
    NO_LOGIN,
    readLoginMessage,
    STARTED_LOGIN,
    type Credential,
    type LoginMethod,
    type LoginView,
    type Provider,
  } from './credentials';

  interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
  }

  const { open, onOpenChange }: Props = $props();

  const COLUMNS: TableColumn[] = [
    { header: 'Name' },
    { header: 'Provider' },
    { header: 'Kind' },
    { header: 'Actions', isMenu: true },
  ];
  const METHODS = [
    { value: 'oauth' as const, label: 'Subscription' },
    { value: 'api_key' as const, label: 'API key' },
  ];
  const SOCKET_PATH = '/ws/assistant';

  let credentials: Credential[] = $state([]);
  let providers: Provider[] = $state([]);
  let loadError: string | null = $state(null);
  let method: LoginMethod = $state('oauth');
  let providerId = $state('');
  let name = $state('');
  let answer = $state('');
  let login: LoginView = $state(NO_LOGIN);
  let socket: WebSocket | null = null;

  const providerItems = $derived(listLoginProviders(providers, method));
  const providerNames = $derived(new Map(providers.map((provider) => [provider.id, provider.name])));

  async function load(): Promise<void> {
    const [credentialResult, providerResult] = await Promise.all([listCredentials(fetch), listProviders(fetch)]);
    loadError = null;
    if (credentialResult.kind === 'ok') {
      credentials = credentialResult.value.credentials;
    } else {
      loadError = credentialResult.message;
    }
    if (providerResult.kind === 'ok') {
      providers = providerResult.value.providers;
    } else {
      loadError = providerResult.message;
    }
  }

  function closeSocket(): void {
    socket?.close();
    socket = null;
  }

  $effect(() => {
    if (open) {
      void load();
    }
    return () => {
      closeSocket();
      login = NO_LOGIN;
    };
  });

  function receive(event: MessageEvent<unknown>): void {
    const message = typeof event.data === 'string' ? readLoginMessage(JSON.parse(event.data)) : null;
    if (message === null) {
      return;
    }
    login = addLoginMessage(login, message);
    if (message.type !== 'login_step') {
      closeSocket();
      void load();
    }
  }

  function startLogin(event: SubmitEvent): void {
    event.preventDefault();
    closeSocket();
    login = STARTED_LOGIN;
    answer = '';
    const opened = new WebSocket(buildSocketUrl(SOCKET_PATH, window.location));
    opened.addEventListener('open', () => {
      opened.send(JSON.stringify({ type: 'login_start', provider: providerId, method, name: name.trim() }));
    });
    opened.addEventListener('message', receive);
    // A socket that closes before login_end or error (for example web restarts) ends the login, so the form comes back.
    opened.addEventListener('close', () => {
      if (socket === opened) {
        socket = null;
        login = addLoginMessage(login, { type: 'error', message: 'The login connection closed. Start the login again.' });
      }
    });
    socket = opened;
  }

  function sendAnswer(event: SubmitEvent): void {
    event.preventDefault();
    if (login.prompt?.prompt_id == null) {
      return;
    }
    socket?.send(JSON.stringify({ type: 'login_answer', prompt_id: login.prompt.prompt_id, value: answer }));
    answer = '';
    login = answerPrompt(login);
  }

  async function removeCredential(credential: Credential): Promise<void> {
    const deleteError = await deleteCredential(fetch, credential.id);
    await load();
    // load() clears the error, so the delete error comes after it.
    if (deleteError !== null) {
      loadError = deleteError;
    }
  }

  /** A change of the kind also stops a login that runs. */
  function selectMethod(value: LoginMethod): void {
    if (value === method) {
      return;
    }
    closeSocket();
    login = NO_LOGIN;
    method = value;
    providerId = '';
  }

  function setAnswer(value: string): void {
    answer = value;
  }

  function setProviderId(value: string): void {
    providerId = value;
  }

  function readOptionItems(options: { id: string; label: string }[] | null): SelectItem<string>[] {
    return (options ?? []).map((option) => ({ value: option.id, label: option.label }));
  }

  function describeAnswerButton(promptType: string | null): string {
    switch (promptType) {
      case 'secret':
        return 'Save API key';
      case 'manual_code':
        return 'Send code';
      default:
        return 'Send answer';
    }
  }
</script>

<Dialog {open} {onOpenChange} title="Credentials" size="lg">
  <div class="credentials">
    {#if loadError !== null}
      <InlineNotification kind="error" title={loadError} />
    {/if}
    <ScrollRegion label="Credentials" maxHeight="16rem">
      <DataTable columns={COLUMNS} size="md">
        {#snippet rows()}
          {#each credentials as credential (credential.id)}
            {@const state = describeCredentialState(credential)}
            <tr>
              <th scope="row"><StatusIndicator kind={state.kind} label={state.label} />{credential.name}</th>
              <td>{providerNames.get(credential.provider) ?? credential.provider}</td>
              <td>
                {describeCredentialKind(credential.type)}
                {#if credential.key_last4 !== null}<span class="credentials__key">{formatKey(credential)}</span>{/if}
              </td>
              <td class="cds--table-column-menu">
                <OverflowMenu
                  label={`Actions for ${credential.name}`}
                  size="md"
                  items={[{ label: 'Delete credential', danger: true, onSelect: () => void removeCredential(credential) }]}
                />
              </td>
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </ScrollRegion>

    <ContentSwitcher label="Credential kind" items={METHODS} value={method} onValueChange={selectMethod} />

    {#if login.phase === 'running'}
      <div class="credentials__steps" aria-live="polite">
        {#if login.authUrl !== null}
          <p>
            <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- the authorization page of the provider. -->
            <a class="cds--link" href={login.authUrl} target="_blank" rel="noreferrer">Open the authorization page</a>
            {#if login.authInstructions !== null}<span>{login.authInstructions}</span>{/if}
          </p>
        {/if}
        {#if login.deviceCode !== null}
          <p>
            <span class="credentials__code">{login.deviceCode.userCode}</span>
            {#if login.deviceCode.url !== null}
              <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- the device page of the provider. -->
              <a class="cds--link" href={login.deviceCode.url} target="_blank" rel="noreferrer">{login.deviceCode.url}</a>
            {/if}
          </p>
        {/if}
        {#if login.progress !== null}
          <p>{login.progress}</p>
        {/if}
        {#if isLoginWaiting(login)}
          <StatusIndicator kind="in-progress" label="Waiting for the provider" align="right" />
        {/if}
        {#if login.prompt !== null}
          <form class="credentials__form" onsubmit={sendAnswer}>
            {#if login.prompt.prompt_type === 'select'}
              <Select
                label={login.prompt.message ?? 'Option'}
                items={readOptionItems(login.prompt.options)}
                value={answer}
                onValueChange={setAnswer}
              />
            {:else}
              <TextInput
                label={login.prompt.message ?? 'Answer'}
                type={login.prompt.prompt_type === 'secret' ? 'password' : 'text'}
                autocomplete="off"
                bind:value={answer}
              />
            {/if}
            <Button type="submit" disabled={answer === ''} title={answer === '' ? 'Enter a value first.' : undefined}>
              {describeAnswerButton(login.prompt.prompt_type)}
            </Button>
          </form>
        {/if}
      </div>
    {:else}
      {#if login.error !== null}
        <InlineNotification kind="error" title={login.error} />
      {/if}
      <form class="credentials__form" onsubmit={startLogin}>
        <Select label="Provider" items={providerItems} value={providerId} onValueChange={setProviderId} />
        <TextInput label="Name" autocomplete="off" bind:value={name} />
        <Button
          type="submit"
          disabled={providerId === '' || name.trim() === ''}
          title={providerId === '' || name.trim() === '' ? 'Select a provider and enter a name first.' : undefined}
        >
          {method === 'oauth' ? 'Log in' : 'Add API key'}
        </Button>
      </form>
    {/if}
  </div>
</Dialog>

<style>
  .credentials {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-06);
  }

  .credentials__form {
    display: flex;
    align-items: flex-end;
    gap: var(--cds-spacing-05);
  }

  .credentials__form > :global(*:not(button)) {
    flex: 1 1 0;
  }

  .credentials__steps {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-04);
  }

  .credentials__steps p {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: var(--cds-spacing-04);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
  }

  .credentials__key {
    margin-inline-start: var(--cds-spacing-03);
    font-family: var(--cds-code-01-font-family);
    font-size: var(--cds-code-01-font-size);
  }

  /* The device code: the user types it on the page of the provider. */
  .credentials__code {
    font-family: var(--cds-code-02-font-family);
    font-size: var(--cds-code-02-font-size);
    font-weight: var(--cds-heading-compact-02-font-weight);
  }
</style>
