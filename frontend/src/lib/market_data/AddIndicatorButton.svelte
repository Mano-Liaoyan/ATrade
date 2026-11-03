<!-- "Add indicator" of a bar chart panel header line (docs/architecture/indicator.md section 23.9.5): a ghost icon
     button and the "/" key open a CommandDialog with one row for each catalog indicator, in catalog order. Enter or a
     click on a row adds the indicator with the catalog defaults. -->
<script lang="ts">
  import ChartLineData16 from '@carbon/icons/es/chart--line--data/16.js';
  import { IconButton } from '#lib/foundation/carbon';
  import { CommandDialog, type CommandDialogItem } from '#lib/foundation/command_dialog';
  import { isAddIndicatorShortcut, type ChartIndicatorDefinition } from './chart_indicators';

  interface Props {
    catalog: ChartIndicatorDefinition[];
    onAdd: (definition: ChartIndicatorDefinition) => void;
    /** Why an indicator cannot be added now, or undefined when it can. */
    findDisabledText?: (definition: ChartIndicatorDefinition) => string | undefined;
  }

  const { catalog, onAdd, findDisabledText = () => undefined }: Props = $props();

  let open = $state(false);

  const items: CommandDialogItem[] = $derived(
    catalog.map((definition) => ({
      value: definition.key,
      label: definition.name,
      // The short name shows only when it is different from the name.
      ...(definition.short_name === definition.name ? {} : { detail: definition.short_name }),
      keywords: [definition.short_name, definition.key],
      ...withDisabledText(findDisabledText(definition)),
    })),
  );

  function withDisabledText(disabledText: string | undefined): { disabledText?: string } {
    return disabledText === undefined ? {} : { disabledText };
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
/>
