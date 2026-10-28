<!-- The Start forward test dialog of the strategy workbench: the instrument, the live bar period, and the optional end
     time of a forward test of the open strategy version. The fields are those of the forward test form
     (routes/forward-tests). -->
<script lang="ts">
  import { Dialog, InlineNotification, Select, TextInput } from '#lib/foundation/carbon';
  import { isLiveBarPeriod, readEndTimeUtc, startForwardTest, type ForwardTest } from '#lib/forward_test';
  import { BAR_PERIODS, DEFAULT_BAR_PERIOD, type BarPeriod } from '#lib/market_data';

  interface Props {
    open: boolean;
    /** The dialog title names the strategy version, for example "Start forward test of SMA v2". */
    title: string;
    strategyVersionId: number | null;
    onOpenChange: (open: boolean) => void;
    onStarted: (forwardTest: ForwardTest) => void;
  }

  const { open, title, strategyVersionId, onOpenChange, onStarted }: Props = $props();

  const liveBarPeriods = BAR_PERIODS.filter((period) => isLiveBarPeriod(period.value));
  // The longest symbol, exchange, and currency that the API takes.
  const MAX_FIELD_LENGTH = 32;

  let symbol = $state('');
  let exchange = $state('');
  let currency = $state('USD');
  let barPeriod = $state<BarPeriod>(DEFAULT_BAR_PERIOD);
  // The value of the datetime-local input: a local time, or '' for no end time.
  let endTimeLocal = $state('');
  let startError = $state('');
  let isStarting = $state(false);
  let form: HTMLFormElement | undefined = $state();

  $effect(() => {
    if (open) {
      startError = '';
    }
  });

  async function submitForwardTest(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    if (strategyVersionId === null) {
      return;
    }
    isStarting = true;
    startError = '';
    const result = await startForwardTest(fetch, {
      strategy_version_id: strategyVersionId,
      symbol: symbol.trim().toUpperCase(),
      exchange: exchange.trim().toUpperCase(),
      currency: currency.trim().toUpperCase(),
      bar_period: barPeriod,
      end_time_utc: readEndTimeUtc(endTimeLocal),
    });
    isStarting = false;
    if (result.kind === 'failed') {
      startError = result.message;
      return;
    }
    onStarted(result.forwardTest);
    onOpenChange(false);
  }
</script>

<Dialog
  {open}
  {onOpenChange}
  {title}
  size="md"
  primaryText={isStarting ? 'Starting…' : 'Start forward test'}
  busy={isStarting}
  onPrimary={() => form?.requestSubmit()}
>
  <form class="forward-test-form" aria-label="Forward test" bind:this={form} onsubmit={submitForwardTest}>
    <TextInput label="Symbol" autocomplete="off" required maxlength={MAX_FIELD_LENGTH} bind:value={symbol} />
    <TextInput label="Exchange" autocomplete="off" required maxlength={MAX_FIELD_LENGTH} bind:value={exchange} />
    <TextInput label="Currency" autocomplete="off" required maxlength={MAX_FIELD_LENGTH} bind:value={currency} />
    <Select
      label="Bar period"
      items={liveBarPeriods}
      value={barPeriod}
      onValueChange={(period: BarPeriod) => {
        barPeriod = period;
      }}
    />
    <TextInput label="End time (local, optional)" type="datetime-local" bind:value={endTimeLocal} />
  </form>
  {#if startError !== ''}
    <InlineNotification
      kind="error"
      title="Forward test not started"
      subtitle={startError}
      lowContrast
      onClose={() => (startError = '')}
    />
  {/if}
</Dialog>

<style>
  .forward-test-form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--cds-spacing-05);
    margin-block-end: var(--cds-spacing-05);
  }
</style>
