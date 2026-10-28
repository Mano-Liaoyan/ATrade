<!-- Strategy page of one strategy: the strategy workbench (StrategyWorkbench). -->
<script lang="ts">
  import { page } from '$app/state';
  import StrategyWorkbench from '../StrategyWorkbench.svelte';

  const strategyId = $derived(Number(page.params['strategyId']));
</script>

<StrategyWorkbench {strategyId} />
