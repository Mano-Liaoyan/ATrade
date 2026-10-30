<!-- The "New parameter sweep" dialog (docs/architecture/backtest.md section 10.11.4): the fields of the "New backtest"
     form (BacktestRequestFields) and 1 row for each parameter of the strategy version: the name, the default value,
     the check box that adds the parameter to the sweep, and the start, end, and step inputs. The run count changes
     while the user types. "Start parameter sweep" is disabled with its reason when the grid has no parameter, more
     than 3 parameters, a range without values, or more than 200 runs. A bool parameter uses both values. -->
<script lang="ts">
  import type { BacktestRequest } from '#lib/backtest';
  import { Checkbox, Dialog, InlineNotification, type NotificationMessage } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import {
    buildSweepGrid,
    countSweepRuns,
    readSweepParameters,
    readSweepStartBlock,
    startSweep,
    type SweepDetail,
    type SweepParameterInput,
  } from '#lib/sweep';
  import BacktestRequestFields from '../backtests/BacktestRequestFields.svelte';

  interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onStarted: (sweep: SweepDetail) => void;
  }

  const { open, onOpenChange, onStarted }: Props = $props();

  const FAILED_TITLE = 'Parameter sweep not started';
  const BLOCK_ID = 'sweep-start-block';
  type RangeField = 'start' | 'end' | 'step';
  const RANGE_FIELDS: { field: RangeField; label: string }[] = [
    { field: 'start', label: 'Start' },
    { field: 'end', label: 'End' },
    { field: 'step', label: 'Step' },
  ];

  let startError = $state<NotificationMessage | null>(null);
  let isStarting = $state(false);
  let fieldsBlockReason = $state<string | null>(null);
  let strategyVersionId = $state('');
  let parameterRows = $state<(SweepParameterInput & { defaultValue: string })[]>([]);
  let form: HTMLFormElement | undefined = $state();
  let fieldsRequest = $state<BacktestRequest | null>(null);

  const grid = $derived(buildSweepGrid(parameterRows));
  const runCount = $derived(countSweepRuns(grid));
  const blockReason = $derived(fieldsBlockReason ?? readSweepStartBlock(grid) ?? null);

  // A new strategy version has its own parameters. A range starts at the default value with step 1.
  $effect(() => {
    const versionId = strategyVersionId;
    parameterRows = [];
    if (versionId === '') {
      return;
    }
    void readSweepParameters(fetch, Number(versionId)).then((result) => {
      if (result.kind === 'failed') {
        startError = { kind: 'error', title: 'Parameters not read', subtitle: result.message };
        return;
      }
      parameterRows = result.value.parameters.map((parameter) => {
        const defaultValue = String(parameter.default);
        const isBool = parameter.type === 'bool';
        return {
          name: parameter.name,
          type: parameter.type,
          defaultValue,
          isSwept: false,
          start: isBool ? '' : defaultValue,
          end: isBool ? '' : defaultValue,
          step: isBool ? '' : '1',
        };
      });
    });
  });

  async function submitSweep(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    const request = fieldsRequest;
    if (blockReason !== null) {
      return;
    }
    if (request === null) {
      startError = { kind: 'error', title: FAILED_TITLE, subtitle: 'Select a strategy version and an instrument.' };
      return;
    }
    isStarting = true;
    startError = null;
    const result = await startSweep(fetch, { ...request, grid });
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
  title="New parameter sweep"
  size="lg"
  primaryText={isStarting ? 'Starting…' : 'Start parameter sweep'}
  busy={isStarting}
  primaryDisabled={blockReason !== null}
  primaryDescribedBy={BLOCK_ID}
  onPrimary={() => form?.requestSubmit()}
>
  <form class="sweep-form" aria-label="Start a parameter sweep" bind:this={form} onsubmit={submitSweep}>
    <BacktestRequestFields
      bind:strategyVersionId
      {open}
      onRequestChange={(request: BacktestRequest | null, reason: string | null) => {
        fieldsRequest = request;
        fieldsBlockReason = reason;
      }}
      onError={(error: NotificationMessage | null) => {
        startError = error;
      }}
    />
    <div class="parameters">
      <ScrollRegion label="Parameters">
        <table class="cds--data-table cds--data-table--sm" aria-label="Parameters">
          <thead>
            <tr>
              <th class="cds--table-column-checkbox"><span class="cds--visually-hidden">Sweep</span></th>
              <th><div class="cds--table-header-label">Parameter</div></th>
              <th align="right"><div class="cds--table-header-label">Default</div></th>
              {#each RANGE_FIELDS as range (range.field)}
                <th align="right"><div class="cds--table-header-label">{range.label}</div></th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each parameterRows as row (row.name)}
              <tr>
                <td class="cds--table-column-checkbox">
                  <Checkbox
                    label={`Sweep ${row.name}`}
                    hideLabel
                    checked={row.isSwept}
                    onCheckedChange={(isChecked: boolean) => {
                      row.isSwept = isChecked;
                    }}
                  />
                </td>
                <th scope="row">{row.name}</th>
                <td align="right" class="number">{row.defaultValue}</td>
                {#each RANGE_FIELDS as range (range.field)}
                  <td>
                    <input
                      class="cds--text-input cds--text-input--sm number"
                      inputmode="decimal"
                      aria-label={`${range.label} of ${row.name}`}
                      disabled={!row.isSwept || row.type === 'bool'}
                      bind:value={row[range.field]}
                    />
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </ScrollRegion>
    </div>
    <p class="run-count cds--form__helper-text" role="status" aria-label="Run count">
      <span class="number">{runCount} {runCount === 1 ? 'run' : 'runs'}</span>
      {#if blockReason !== null}
        <span id={BLOCK_ID} class="block-reason">{blockReason}</span>
      {/if}
    </p>
  </form>
  {#if startError !== null}
    <InlineNotification {...startError} lowContrast onClose={() => (startError = null)} />
  {/if}
</Dialog>

<style>
  .sweep-form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--cds-spacing-05);
    margin-block-end: var(--cds-spacing-05);
  }

  .sweep-form :global(input.number),
  .number {
    font-variant-numeric: tabular-nums;
    text-align: end;
  }

  .parameters {
    display: flex;
    grid-column: 1 / -1;
    flex-direction: column;
    max-block-size: 16rem;
  }

  .run-count {
    display: flex;
    grid-column: 1 / -1;
    gap: var(--cds-spacing-05);
    margin: 0;
  }

  .block-reason {
    color: var(--cds-text-error);
  }
</style>
