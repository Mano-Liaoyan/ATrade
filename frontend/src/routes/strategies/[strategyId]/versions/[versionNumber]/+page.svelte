<!-- Strategy page of one strategy version: the strategy workbench (StrategyWorkbench) opens this version. The strategy
     links "<name> vN" of the backtest and forward test pages open this address. -->
<script lang="ts">
  import { page } from '$app/state';
  import StrategyWorkbench from '../../../StrategyWorkbench.svelte';

  const strategyId = $derived(Number(page.params['strategyId']));
  const versionNumber = $derived(Number(page.params['versionNumber']));
</script>

<StrategyWorkbench {strategyId} {versionNumber} />
