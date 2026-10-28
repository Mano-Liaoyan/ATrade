<!-- The frame of each lightweight-charts chart: the canvas container (role img) and the one TradingView attribution
     under it. Every chart of ATrade uses this frame, so all charts show the same attribution (spec #99).
     With `fill`, the frame fills the height of its parent and the canvas takes the rest of the height. The chart then
     needs `autoSize`: lightweight-charts follows the size of the canvas container, for example after a side column
     collapses or the window changes.

     Attribution notice of lightweight-charts (Apache License 2.0):
     TradingView Lightweight Charts™
     Copyright (c) 2025 TradingView, Inc. https://www.tradingview.com/
     The chart shows the TradingView attribution logo, and the text under the chart links to TradingView. -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    /** The accessible name of the chart. */
    label: string;
    /** The canvas container. The chart component creates the chart in it. */
    canvas?: HTMLDivElement;
    fill?: boolean;
    /** The canvas height without `fill`. */
    height?: string;
    minHeight?: string;
    /** Content between the canvas and the attribution, for example a legend. */
    children?: Snippet;
  }

  let {
    label,
    canvas = $bindable(),
    fill = false,
    height = 'min(32rem, 60vh)',
    minHeight = '16rem',
    children,
  }: Props = $props();
</script>

<figure class={['chart-frame', fill && 'chart-frame--fill']}>
  <div
    class="chart-canvas"
    role="img"
    aria-label={label}
    style:height={fill ? undefined : height}
    style:min-height={fill ? undefined : minHeight}
    bind:this={canvas}
  ></div>
  {@render children?.()}
  <figcaption class="chart-attribution">
    Chart by <a class="cds--link cds--link--sm" href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer">TradingView</a>
    Lightweight Charts™
  </figcaption>
</figure>

<style>
  .chart-frame {
    margin: 0;
  }

  .chart-frame--fill {
    display: flex;
    flex-direction: column;
    block-size: 100%;
    min-block-size: 0;
    box-sizing: border-box;
  }

  .chart-canvas {
    position: relative;
    overflow: hidden;
  }

  .chart-frame--fill .chart-canvas {
    flex: 1;
    min-block-size: 0;
  }

  .chart-attribution {
    flex: none;
    margin-block-start: var(--cds-spacing-03);
    font-size: var(--cds-helper-text-01-font-size);
    line-height: var(--cds-helper-text-01-line-height);
    letter-spacing: var(--cds-helper-text-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .chart-frame--fill .chart-attribution {
    margin-block-start: var(--cds-spacing-02);
  }
</style>
