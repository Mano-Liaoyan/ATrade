<!-- PROTOTYPE (#99), throwaway: the Start forward test dialog of the strategy workbench. It has the fields of the PR #98
     forward test form. The strategy version is the open version of the workbench. -->
<script lang="ts">
  import { Dialog, InlineNotification, Select, TextInput } from '#lib/foundation/carbon';
  import { isLiveBarPeriod, readEndTimeUtc, startForwardTest, type ForwardTest } from '#lib/forward_test';
  import { BAR_PERIODS, DEFAULT_BAR_PERIOD, type BarPeriod } from '#lib/market_data';

  interface Props {
    open: boolean;
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
  let endTimeLocal = $state('');
  let startError = $state('');
  let isStarting = $state(false);

  async function start(): Promise<void> {
    if (strategyVersionId === null || symbol.trim() === '' || exchange.trim() === '') {
      startError = 'Type a symbol and an exchange.';
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
  primaryText="Start forward test"
  busy={isStarting}
  onPrimary={() => {
    void start();
  }}
>
  <div class="forward-test-fields">
    <TextInput label="Symbol" bind:value={symbol} required maxlength={MAX_FIELD_LENGTH} />
    <TextInput label="Exchange" bind:value={exchange} required maxlength={MAX_FIELD_LENGTH} />
    <TextInput label="Currency" bind:value={currency} required maxlength={MAX_FIELD_LENGTH} />
    <Select
      label="Bar period"
      items={liveBarPeriods}
      value={barPeriod}
      onValueChange={(period: BarPeriod) => {
        barPeriod = period;
      }}
    />
    <TextInput label="End time (local, optional)" type="datetime-local" bind:value={endTimeLocal} />
  </div>
  {#if startError !== ''}
    <InlineNotification kind="error" lowContrast title="Forward test not started" subtitle={startError} />
  {/if}
</Dialog>

<style>
  .forward-test-fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--cds-spacing-05);
    margin-block-end: var(--cds-spacing-05);
  }
</style>
