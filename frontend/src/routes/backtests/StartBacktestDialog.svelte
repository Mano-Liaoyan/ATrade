<!-- The "New backtest" dialog of the backtest workbench: the form that starts a backtest with the fields of
     BacktestRequestFields. The form id is START_BACKTEST_FORM_ID: the command palette opens the dialog with it. With
     `strategyVersion`, each open selects that strategy version, for example the open version of the strategy page
     (Run backtest). -->
<script lang="ts">
  import { startBacktest, type Backtest, type BacktestRequest } from '#lib/backtest';
  import { Dialog, InlineNotification, type NotificationMessage } from '#lib/foundation/carbon';
  import type { StrategyVersionKey } from '#lib/strategy';
  import { START_BACKTEST_FORM_ID } from '../palette_commands';
  import BacktestRequestFields from './BacktestRequestFields.svelte';

  interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onStarted: (backtest: Backtest) => void;
    strategyVersion?: StrategyVersionKey | null;
  }

  const { open, onOpenChange, onStarted, strategyVersion = null }: Props = $props();

  const FAILED_TITLE = 'Backtest not started';

  let startError = $state<NotificationMessage | null>(null);
  let isStarting = $state(false);
  let blockReason = $state<string | null>(null);
  let form: HTMLFormElement | undefined = $state();
  let fieldsRequest = $state<BacktestRequest | null>(null);

  async function submitBacktest(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    const request = fieldsRequest;
    if (request === null) {
      startError = { kind: 'error', title: FAILED_TITLE, subtitle: 'Select a strategy version and an instrument.' };
      return;
    }
    isStarting = true;
    startError = null;
    const result = await startBacktest(fetch, request);
    isStarting = false;
    if (result.kind === 'failed') {
      startError = { kind: 'error', title: FAILED_TITLE, subtitle: result.message };
      return;
    }
    onStarted(result.value);
    onOpenChange(false);
  }
</script>

<Dialog
  {open}
  {onOpenChange}
  title="New backtest"
  size="md"
  primaryText={isStarting ? 'Starting…' : 'Start backtest'}
  busy={isStarting}
  primaryDisabled={blockReason !== null}
  primaryDescribedBy="top-n-error"
  onPrimary={() => form?.requestSubmit()}
>
  <form
    id={START_BACKTEST_FORM_ID}
    class="backtest-form"
    aria-label="Start a backtest"
    bind:this={form}
    onsubmit={submitBacktest}
  >
    <BacktestRequestFields
      {open}
      {strategyVersion}
      onRequestChange={(request: BacktestRequest | null, reason: string | null) => {
        fieldsRequest = request;
        blockReason = reason;
      }}
      onError={(error: NotificationMessage | null) => {
        startError = error;
      }}
    />
  </form>
  {#if startError !== null}
    <InlineNotification {...startError} lowContrast onClose={() => (startError = null)} />
  {/if}
</Dialog>

<style>
  .backtest-form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--cds-spacing-05);
    margin-block-end: var(--cds-spacing-05);
  }

  .backtest-form :global(input.number) {
    font-variant-numeric: tabular-nums;
    text-align: end;
  }
</style>
