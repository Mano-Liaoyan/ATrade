<!-- The Strategy select and the Strategy version select of a start form. The selects have no wrapper element, so they
     are cells of the form grid. Each open reads the strategies again and, with `strategyVersion`, selects that strategy
     version. A new strategy selects its latest version. -->
<script lang="ts">
  import { Select, type NotificationMessage } from '#lib/foundation/carbon';
  import { listStrategies, readStrategy, type StrategyDetail, type StrategyListItem } from './strategy_api';
  import { formatVersionLabel, type StrategyVersionKey } from './strategy_drafts';

  interface Props {
    open: boolean;
    onError: (error: NotificationMessage) => void;
    strategyVersion?: StrategyVersionKey | null;
    /** The selected strategy version ID, or an empty text. */
    strategyVersionId?: string;
  }

  let { open, onError, strategyVersion = null, strategyVersionId = $bindable('') }: Props = $props();

  let strategies: StrategyListItem[] = $state([]);
  let selectedStrategy = $state<StrategyDetail | null>(null);
  let strategyId = $state('');
  const strategyItems = $derived(strategies.map((strategy) => ({ value: String(strategy.id), label: strategy.name })));
  const versionItems = $derived(
    selectedStrategy === null
      ? []
      : selectedStrategy.versions.map((version) => ({
          value: String(version.id),
          label: formatVersionLabel(selectedStrategy?.name ?? '', version.version_number),
        })),
  );

  $effect(() => {
    if (!open) {
      return;
    }
    if (strategyVersion !== null) {
      void selectStrategy(String(strategyVersion.strategyId), String(strategyVersion.versionId));
    }
    void listStrategies(fetch).then((result) => {
      if (result.kind === 'ok') {
        strategies = result.value;
      }
    });
  });

  // Without a version id, the latest version of the strategy is selected.
  async function selectStrategy(selectedId: string, versionId: string | null = null): Promise<void> {
    strategyId = selectedId;
    selectedStrategy = null;
    strategyVersionId = '';
    const result = await readStrategy(fetch, Number(selectedId));
    if (result.kind === 'failed') {
      onError({ kind: 'error', title: 'Strategy not read', subtitle: result.message });
      return;
    }
    selectedStrategy = result.value;
    const latestVersion = result.value.versions.at(-1);
    strategyVersionId = versionId ?? (latestVersion === undefined ? '' : String(latestVersion.id));
  }
</script>

<Select
  label="Strategy"
  placeholder="Select a strategy"
  items={strategyItems}
  value={strategyId}
  onValueChange={(selectedId: string) => void selectStrategy(selectedId)}
/>
<Select
  label="Strategy version"
  placeholder="Select a strategy first"
  items={versionItems}
  value={strategyVersionId}
  disabled={versionItems.length === 0}
  onValueChange={(versionId: string) => {
    strategyVersionId = versionId;
  }}
/>
