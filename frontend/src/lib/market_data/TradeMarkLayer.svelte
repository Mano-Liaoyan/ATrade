<!-- The HTML part of the trade marks of BarChart (docs/architecture/indicator.md section 23.9.9). The series primitive
     draws the marks on the canvas. Over the canvas: the tooltip of the mark under the pointer, a Carbon popover with
     one line for each trade of the mark (IBM Plex Mono, tabular numbers). For screen readers and tests: the "Trade
     marks" list, one item for each mark, with the place of the mark center in chart pixels and its focus ring. -->
<script lang="ts">
  import { formatTradeLine, readMarkBounds, type ChartTrade, type TradeMarkBox } from './trade_marks';

  interface Props {
    boxes: TradeMarkBox[];
    trades: ChartTrade[];
    hoveredMarkKey: string | null;
    ringTrades: number[];
  }

  const { boxes, trades, hoveredMarkKey, ringTrades }: Props = $props();

  function readKey(box: TradeMarkBox): string {
    return `${String(box.mark.barIndex)}:${box.mark.side}`;
  }

  function listLines(box: TradeMarkBox): ReturnType<typeof formatTradeLine>[] {
    return box.mark.tradeIndexes.flatMap((tradeIndex) => {
      const trade = trades[tradeIndex];
      return trade === undefined ? [] : [formatTradeLine(trade)];
    });
  }

  const hoveredBox = $derived(boxes.find((box) => readKey(box) === hoveredMarkKey));
</script>

<div class="trade-mark-layer">
  {#if hoveredBox !== undefined}
    {@const bounds = readMarkBounds(hoveredBox)}
    <span
      class={[
        'cds--popover-container',
        'cds--popover--caret',
        'cds--popover--open',
        hoveredBox.mark.side === 'BUY' ? 'cds--popover--bottom' : 'cds--popover--top',
        'trade-mark-tooltip',
      ]}
      style:left={`${String(bounds.left)}px`}
      style:top={`${String(bounds.top)}px`}
      style:width={`${String(bounds.width)}px`}
      style:height={`${String(bounds.height)}px`}
      role="tooltip"
    >
      <span class="cds--popover">
        <span class="cds--popover-content">
          {#each listLines(hoveredBox) as line, lineIndex (lineIndex)}
            <span class="trade-line">
              {line.text}{#if line.profit !== null}<span class={['trade-profit', `trade-profit--${line.profit.kind}`]}>{line.profit.text}</span>{/if}
            </span>
          {/each}
        </span>
        <span class="cds--popover-caret"></span>
      </span>
    </span>
  {/if}
  <ul class="cds--visually-hidden" aria-label="Trade marks">
    {#each boxes as box (readKey(box))}
      <li
        data-side={box.mark.side}
        data-x={Math.round(box.x)}
        data-y={Math.round(readMarkBounds(box).centerY)}
        data-ring={box.mark.tradeIndexes.some((tradeIndex) => ringTrades.includes(tradeIndex))}
      >
        {listLines(box)
          .map((line) => (line.profit === null ? line.text : `${line.text} ${line.profit.text}`))
          .join('; ')}
      </li>
    {/each}
  </ul>
</div>

<style>
  .trade-mark-layer {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  .trade-mark-tooltip {
    position: absolute;
  }

  .trade-mark-tooltip .cds--popover-content {
    display: flex;
    flex-direction: column;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
    font-family: var(--cds-code-01-font-family, 'IBM Plex Mono', monospace);
    font-size: var(--cds-code-01-font-size);
    line-height: var(--cds-code-01-line-height);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .trade-profit {
    margin-inline-start: var(--cds-spacing-04);
  }

  .trade-profit--success {
    color: var(--cds-support-success);
  }

  .trade-profit--error {
    color: var(--cds-support-error);
  }
</style>
