<!-- Strategy editor. PROTOTYPE (#99): ?variant=current shows the PR #98 page, the default shows the workbench. -->
<script lang="ts">
  import { page } from '$app/state';
  import { readPrototypeVariant } from '#lib/foundation/prototype_switcher';
  import StrategyWorkbenchPrototype from '../StrategyWorkbenchPrototype.svelte';
  import CurrentStrategyPage from './CurrentStrategyPage.svelte';

  const variant = $derived(readPrototypeVariant(page.url.searchParams));
  const strategyId = $derived(Number(page.params['strategyId']));
</script>

{#if variant === 'current'}
  <CurrentStrategyPage />
{:else}
  <StrategyWorkbenchPrototype {strategyId} />
{/if}
