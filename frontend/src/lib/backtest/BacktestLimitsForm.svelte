<!-- The backtest limits: the timeout in minutes and the number of backtests that run at the same time. PostgreSQL
     stores them. A change applies to the next backtest that starts. -->
<script lang="ts">
  import { changeBacktestLimits, readBacktestLimits } from './backtest_api';
  import { convertTimeoutMinutesToSeconds, formatTimeoutMinutes } from './backtest_format';

  let timeoutMinutes = $state('');
  // The backend checks the range of the concurrency (1 to 16). The form shows its reason.
  let concurrency = $state('');
  let statusMessage = $state('');
  let errorMessage = $state('');
  let isSaving = $state(false);

  $effect(() => {
    void readBacktestLimits(fetch).then((result) => {
      if (result.kind === 'failed') {
        errorMessage = result.message;
        return;
      }
      timeoutMinutes = formatTimeoutMinutes(result.value.timeout_seconds);
      concurrency = String(result.value.concurrency);
    });
  });

  async function saveLimits(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    statusMessage = '';
    errorMessage = '';
    const timeoutSeconds = convertTimeoutMinutesToSeconds(timeoutMinutes);
    if (timeoutSeconds === null) {
      errorMessage = 'The timeout must be a whole number of minutes above 0.';
      return;
    }
    isSaving = true;
    const result = await changeBacktestLimits(fetch, { timeout_seconds: timeoutSeconds, concurrency: Number(concurrency) });
    isSaving = false;
    if (result.kind === 'failed') {
      errorMessage = result.message;
      return;
    }
    timeoutMinutes = formatTimeoutMinutes(result.value.timeout_seconds);
    concurrency = String(result.value.concurrency);
    statusMessage = 'Saved. The limits apply to the next backtest that starts.';
  }
</script>

<form class="limits-form" aria-label="Backtest limits" onsubmit={saveLimits}>
  <label>
    Timeout (minutes)
    <input inputmode="numeric" bind:value={timeoutMinutes} required />
  </label>
  <label>
    Backtests at the same time
    <input inputmode="numeric" bind:value={concurrency} required />
  </label>
  <button type="submit" disabled={isSaving}>Save limits</button>
</form>
<p class="message" role="status" aria-label="Backtest limits status">{statusMessage}</p>
{#if errorMessage !== ''}
  <p class="error" role="alert">{errorMessage}</p>
{/if}

<style>
  .limits-form {
    display: flex;
    flex-wrap: wrap;
    align-items: end;
    gap: 0.75rem;
  }

  .limits-form label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .message {
    min-block-size: 1.25rem;
  }

  .error {
    color: var(--color-warning);
  }
</style>
