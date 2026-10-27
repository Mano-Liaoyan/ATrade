<!-- Strategy list: each strategy with its latest version, and a form that creates a strategy from the template. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { createStrategy, formatVersionLabel, listStrategies, type StrategyListItem } from '#lib/strategy';

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
  <label>
    Strategy name
    <input name="name" bind:value={newName} required maxlength="100" />
  </label>
  <button type="submit" disabled={isCreating}>Create strategy</button>
</form>
{#if createError !== ''}
  <p class="error" role="alert">{createError}</p>
{/if}

{#if loadError !== ''}
  <p class="error" role="alert">{loadError}</p>
{:else if strategies.length === 0}
  <p>No strategy yet. A new strategy starts from a template.</p>
{:else}
  <ul class="strategy-list">
    {#each strategies as strategy (strategy.id)}
      <li>
        <a href={resolve('/strategies/[strategyId]', { strategyId: String(strategy.id) })}>
          {formatVersionLabel(strategy.name, strategy.latest_version_number)}
        </a>
      </li>
    {/each}
  </ul>
{/if}

<style>
  .create-form {
    display: flex;
    align-items: end;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .create-form label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .error {
    color: #cf222e;
  }

  .strategy-list {
    padding-left: 1.25rem;
  }
</style>
