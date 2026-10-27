<!-- The backtest limits: the timeout in minutes and the number of backtests that run at the same time. PostgreSQL
     stores them. A change applies to the next backtest that starts. -->
<script lang="ts">
  import { Button, InlineNotification, TextInput } from '#lib/foundation/carbon';
  import { changeBacktestLimits, readBacktestLimits } from './backtest_api';
  import { convertTimeoutMinutesToSeconds, formatTimeoutMinutes } from './backtest_format';

  let timeoutMinutes = $state('');
  // The backend checks the range of the concurrency (1 to 16). The form shows its reason.
  let concurrency = $state('');
  let timeoutError = $state<string | null>(null);
  let result = $state<{ isError: boolean; title: string; subtitle: string } | null>(null);
  let isSaving = $state(false);

  $effect(() => {
    void readBacktestLimits(fetch).then((readResult) => {
      if (readResult.kind === 'failed') {
        result = { isError: true, title: 'Limits not read', subtitle: readResult.message };
        return;
      }
      timeoutMinutes = formatTimeoutMinutes(readResult.value.timeout_seconds);
      concurrency = String(readResult.value.concurrency);
    });
  });

  async function saveLimits(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    result = null;
    const timeoutSeconds = convertTimeoutMinutesToSeconds(timeoutMinutes);
    if (timeoutSeconds === null) {
      timeoutError = 'The timeout must be a whole number of minutes above 0.';
      return;
    }
    timeoutError = null;
    isSaving = true;
    const saveResult = await changeBacktestLimits(fetch, { timeout_seconds: timeoutSeconds, concurrency: Number(concurrency) });
    isSaving = false;
    if (saveResult.kind === 'failed') {
      result = { isError: true, title: 'Limits not saved', subtitle: saveResult.message };
      return;
    }
    timeoutMinutes = formatTimeoutMinutes(saveResult.value.timeout_seconds);
    concurrency = String(saveResult.value.concurrency);
    result = { isError: false, title: 'Limits saved', subtitle: 'They apply to the next backtest that starts.' };
  }
</script>

<form class="limits-form" aria-label="Backtest limits" onsubmit={saveLimits}>
  <TextInput label="Timeout (minutes)" inputmode="numeric" class="number" invalidText={timeoutError} bind:value={timeoutMinutes} required />
  <TextInput label="Backtests at the same time" inputmode="numeric" class="number" bind:value={concurrency} required />
  <div>
    <Button type="submit" size="md" disabled={isSaving}>Save limits</Button>
  </div>
</form>
{#if result !== null}
  <InlineNotification
    kind={result.isError ? 'error' : 'success'}
    label={result.isError ? undefined : 'Backtest limits status'}
    title={result.title}
    subtitle={result.subtitle}
    lowContrast
    onClose={() => (result = null)}
  />
{/if}

<style>
  .limits-form {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
    align-items: end;
    gap: var(--cds-spacing-05);
    margin-block-end: var(--cds-spacing-05);
  }

  .limits-form :global(input.number) {
    font-variant-numeric: tabular-nums;
    text-align: end;
  }
</style>
