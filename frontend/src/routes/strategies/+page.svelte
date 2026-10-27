<!-- Strategy list: each strategy with its latest version, and a form that creates a strategy from the template. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { Button, InlineNotification, TextInput } from '#lib/foundation/carbon';
  import { createStrategy, formatVersionLabel, listStrategies, type StrategyListItem } from '#lib/strategy';

  // The backend refuses a longer name.
  const STRATEGY_NAME_MAX_LENGTH = 100;

  let strategies: StrategyListItem[] = $state([]);
  let loadError = $state('');
  let newName = $state('');
  let createError = $state('');
  let isCreating = $state(false);

  $effect(() => {
    void listStrategies(fetch).then((result) => {
      if (result.kind === 'failed') {
        loadError = result.message;
        return;
      }
      strategies = result.value;
    });
  });

  async function submitNewStrategy(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    isCreating = true;
    const result = await createStrategy(fetch, newName);
    isCreating = false;
    if (result.kind === 'failed') {
      createError = result.message;
      return;
    }
    await goto(resolve('/strategies/[strategyId]', { strategyId: String(result.strategy.id) }));
  }
</script>

<h1>Strategies</h1>

<form class="create-form" onsubmit={submitNewStrategy}>
  <div class="create-name">
    <TextInput label="Strategy name" name="name" bind:value={newName} required maxlength={STRATEGY_NAME_MAX_LENGTH} />
  </div>
  <Button type="submit" size="md" disabled={isCreating}>{isCreating ? 'Creating…' : 'Create strategy'}</Button>
</form>
{#if createError !== ''}
  <div class="page-message">
    <InlineNotification kind="error" lowContrast title="Strategy not created" subtitle={createError} />
  </div>
{/if}

{#if loadError !== ''}
  <div class="page-message">
    <InlineNotification kind="error" lowContrast title="Strategies not loaded" subtitle={loadError} />
  </div>
{:else if strategies.length === 0}
  <p class="empty">No strategy yet.</p>
{:else}
  <ul class="strategy-list cds--contained-list cds--contained-list--on-page" aria-label="Strategies">
    {#each strategies as strategy (strategy.id)}
      <li class="cds--contained-list-item">
        <div class="cds--contained-list-item__content">
          <a class="cds--link" href={resolve('/strategies/[strategyId]', { strategyId: String(strategy.id) })}>
            {formatVersionLabel(strategy.name, strategy.latest_version_number)}
          </a>
        </div>
      </li>
    {/each}
  </ul>
{/if}

<style>
  .create-form {
    display: flex;
    align-items: end;
    gap: var(--cds-spacing-05);
    margin-block: 0 var(--cds-spacing-06);
  }

  .create-name {
    inline-size: calc(2 * var(--cds-spacing-13));
  }

  .page-message {
    margin-block-end: var(--cds-spacing-05);
  }

  .page-message :global(.cds--inline-notification) {
    margin-block: 0;
  }

  .empty {
    margin-block: 0;
    font-size: var(--cds-body-01-font-size);
    line-height: var(--cds-body-01-line-height);
    color: var(--cds-text-secondary);
  }

  .strategy-list {
    max-inline-size: calc(4 * var(--cds-spacing-13));
    margin-block: 0;
    padding: 0;
  }
</style>
