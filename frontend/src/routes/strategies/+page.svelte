<!-- Strategy list. PROTOTYPE (#99): ?variant=current shows the PR #98 page, the default shows the workbench. -->
<script lang="ts">
  import { page } from '$app/state';
  import { readPrototypeVariant } from '#lib/foundation/prototype_switcher';
  import CurrentStrategiesPage from './CurrentStrategiesPage.svelte';
  import StrategyWorkbenchPrototype from './StrategyWorkbenchPrototype.svelte';

  const variant = $derived(readPrototypeVariant(page.url.searchParams));
</script>

{#if variant === 'current'}
  <CurrentStrategiesPage />
{:else}
  <StrategyWorkbenchPrototype strategyId={null} />
{/if}
