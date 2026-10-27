<!-- The forward tests with their actual status from /ws/forward-tests, a stop button for each running one, and a
     "Backtest the same period" button for each one with a start balance (docs/architecture/forward_test.md 12.10). -->
<script lang="ts">
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import {
    canBacktestSamePeriod,
    canStop,
    describeForwardTestStatus,
    stopForwardTest,
    type ForwardTest,
  } from './forward_test_api';

  interface Props {
    forwardTests: ForwardTest[];
    // The page starts the backtest and opens the comparison page.
    onBacktestSamePeriod: (forwardTestId: number) => void;
  }

  const { forwardTests, onBacktestSamePeriod }: Props = $props();

  let stoppingIds = $state<number[]>([]);
  let stopMessage = $state<string | null>(null);

  async function stop(forwardTestId: number): Promise<void> {
    stopMessage = null;
    stoppingIds = [...stoppingIds, forwardTestId];
    const result = await stopForwardTest(fetch, forwardTestId);
    if (result.kind === 'failed') {
      stoppingIds = stoppingIds.filter((stoppingId) => stoppingId !== forwardTestId);
      stopMessage = result.message;
    }
  }
</script>

{#if stopMessage !== null}
  <p class="stop-message" role="alert">{stopMessage}</p>
{/if}
{#if forwardTests.length === 0}
  <p>No forward test yet.</p>
{:else}
  <ScrollRegion label="Forward tests" maxHeight="24rem">
    <table class="forward-tests">
      <thead>
        <tr>
          <th scope="col">Forward test</th>
          <th scope="col">Strategy version</th>
          <th scope="col">Instrument</th>
          <th scope="col">Bar period</th>
          <th scope="col">Status</th>
          <th scope="col">Client ID</th>
          <th scope="col">Start balance (USD)</th>
          <th scope="col">Started (UTC)</th>
          <th scope="col"><span class="visually-hidden">Actions</span></th>
        </tr>
      </thead>
      <tbody>
        {#each forwardTests as forwardTest (forwardTest.id)}
          <tr>
            <th scope="row">#{forwardTest.id}</th>
            <td>{forwardTest.strategy_name} v{forwardTest.version_number}</td>
            <td>{forwardTest.symbol} / {forwardTest.exchange} / {forwardTest.currency}</td>
            <td>{forwardTest.bar_period}</td>
            <td>
              {describeForwardTestStatus(forwardTest.status)}
              {#if forwardTest.error_message !== null}
                <span class="error-message">{forwardTest.error_message}</span>
              {/if}
            </td>
            <td class="number">{forwardTest.client_id ?? ''}</td>
            <td class="number">{forwardTest.start_balance_usd ?? ''}</td>
            <td>{forwardTest.created_at_utc}</td>
            <td>
              <div class="actions">
                {#if canStop(forwardTest)}
                  <button
                    type="button"
                    aria-label={`Stop forward test ${String(forwardTest.id)}`}
                    disabled={stoppingIds.includes(forwardTest.id)}
                    onclick={() => stop(forwardTest.id)}>Stop</button
                  >
                {/if}
                {#if canBacktestSamePeriod(forwardTest)}
                  <button
                    type="button"
                    aria-label={`Backtest the same period as forward test ${String(forwardTest.id)}`}
                    onclick={() => {
                      onBacktestSamePeriod(forwardTest.id);
                    }}>Backtest the same period</button
                  >
                {/if}
              </div>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </ScrollRegion>
{/if}

<style>
  p {
    margin: 0;
  }

  .stop-message,
  .error-message {
    color: var(--color-warning);
  }

  .error-message {
    display: block;
    font-size: 0.75rem;
  }

  .forward-tests {
    border-collapse: collapse;
    inline-size: 100%;
    font-size: 0.875rem;
  }

  .forward-tests th,
  .forward-tests td {
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid var(--color-border);
    text-align: start;
    overflow-wrap: anywhere;
  }

  .forward-tests thead th {
    position: sticky;
    inset-block-start: 0;
    background: var(--color-surface);
  }

  .forward-tests .number {
    text-align: end;
    font-variant-numeric: tabular-nums;
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
  }

  .visually-hidden {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
</style>
