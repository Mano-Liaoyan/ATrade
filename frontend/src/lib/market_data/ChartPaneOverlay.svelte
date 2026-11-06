<!-- The HTML layer over one pane of a bar chart (docs/architecture/indicator.md section 23.9.4): the legend at the top
     left, and the options menu ("Options for <legend name>") at the top right. A legend that is higher than its pane
     scrolls in itself with a visible track (ScrollRegion). The layer takes no pointer events, so the crosshair follows
     the pointer over it. Only the options button, the scroll track, and the parts of the legend rows with buttons take them. -->
<script lang="ts">
  import { OverflowMenu, type OverflowMenuItem } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { LegendBar, LegendRow, LegendRowActions, PaneBox } from './chart_indicators';
  import ChartLegend from './ChartLegend.svelte';

  interface Props {
    box: PaneBox;
    /** The OHLC row of the price pane. Null for an own pane. */
    bar?: LegendBar | null;
    rows: LegendRow[];
    /** The name of the pane in labels: the legend name of its first row, or "bars" for the price pane. */
    name: string;
    menuItems: OverflowMenuItem[];
    /** The buttons of the indicator rows. */
    actions?: LegendRowActions;
  }

  const { box, bar = null, rows, name, menuItems, actions }: Props = $props();
</script>

<div
  class="pane-overlay"
  style:top={`${String(box.top)}px`}
  style:height={`${String(box.height)}px`}
  style:width={`${String(box.width)}px`}
>
  {#if bar !== null || rows.length > 0}
    <div class="pane-legend">
      <ScrollRegion label={`Legend of ${name}`} maxHeight={`calc(${String(box.height)}px - var(--cds-spacing-03))`}>
        <ChartLegend {bar} {rows} {actions} />
      </ScrollRegion>
    </div>
  {/if}
  {#if menuItems.length > 0}
    <div class="pane-options">
      <OverflowMenu label={`Options for ${name}`} items={menuItems} size="sm" horizontal />
    </div>
  {/if}
</div>

<style>
  .pane-overlay {
    position: absolute;
    inset-inline-start: 0;
    z-index: 1;
    pointer-events: none;
  }

  /* The legend leaves room for the options button (32px) at the right. */
  .pane-legend {
    position: absolute;
    inset-block-start: var(--cds-spacing-02);
    inset-inline-start: var(--cds-spacing-03);
    max-inline-size: calc(100% - var(--cds-spacing-03) - var(--cds-spacing-08));
  }

  .pane-legend :global(.scroll-track) {
    pointer-events: auto;
  }

  .pane-options {
    position: absolute;
    inset-block-start: 0;
    inset-inline-end: 0;
    pointer-events: auto;
  }
</style>
