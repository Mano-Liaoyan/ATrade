<!-- "Add indicator" of a bar chart panel header line (docs/architecture/indicator.md section 23.9.5): a ghost icon
     button and the "/" key open a CommandDialog with one row for each catalog indicator, in catalog order. Enter or a
     click on a row adds the indicator with the catalog defaults. With `onToggleFavorite`, each row has a star button
     ("Add <name> to favorite indicators" or "Remove <name> from favorite indicators"), and the favorite indicators
     come first. A click on the star does not add the indicator. The favorite indicators are saved in the chart
     indicator set (ChartIndicatorSetStore). -->
<script lang="ts">
  import ChartLineData16 from '@carbon/icons/es/chart--line--data/16.js';
  import Star16 from '@carbon/icons/es/star/16.js';
  import StarFilled16 from '@carbon/icons/es/star--filled/16.js';
  import { IconButton } from '#lib/foundation/carbon';
  import { CommandDialog, type CommandDialogItem, type CommandDialogItemAction } from '#lib/foundation/command_dialog';
  import { orderByFavorites } from './chart_indicator_set';
  import { isAddIndicatorShortcut, type ChartIndicatorDefinition } from './chart_indicators';

  interface Props {
    catalog: ChartIndicatorDefinition[];
    onAdd: (definition: ChartIndicatorDefinition) => void;
    /** Catalog keys. */
    favorites?: string[];
    /** Without it, the rows have no star button. */
    onToggleFavorite?: (key: string) => void;
  }

  const { catalog, onAdd, favorites = [], onToggleFavorite }: Props = $props();

  let open = $state(false);

  const items: CommandDialogItem[] = $derived(
    orderByFavorites(catalog, onToggleFavorite === undefined ? [] : favorites).map((definition) => ({
      value: definition.key,
      label: definition.name,
      // The short name shows only when it is different from the name.
      ...(definition.short_name === definition.name ? {} : { detail: definition.short_name }),
      keywords: [definition.short_name, definition.key],
      ...(onToggleFavorite === undefined ? {} : { action: favoriteAction(definition) }),
    })),
  );

  function favoriteAction(definition: ChartIndicatorDefinition): CommandDialogItemAction {
    return favorites.includes(definition.key)
      ? { label: `Remove ${definition.name} from favorite indicators`, icon: StarFilled16 }
      : { label: `Add ${definition.name} to favorite indicators`, icon: Star16 };
  }

  function openWithShortcut(event: KeyboardEvent): void {
    if (!open && !event.defaultPrevented && isAddIndicatorShortcut(event)) {
      event.preventDefault();
      open = true;
    }
  }

  function addIndicator(key: string): void {
    const definition = catalog.find((item) => item.key === key);
    if (definition !== undefined) {
      onAdd(definition);
    }
  }
</script>

<svelte:window onkeydown={openWithShortcut} />

<IconButton
  label="Add indicator"
  shortcut="/"
  icon={ChartLineData16}
  onclick={() => {
    open = true;
  }}
/>

<CommandDialog
  {open}
  onOpenChange={(nextOpen: boolean) => {
    open = nextOpen;
  }}
  title="Add indicator"
  searchLabel="Search indicators"
  {items}
  onSelect={addIndicator}
  onAction={(key: string) => {
    onToggleFavorite?.(key);
  }}
/>
