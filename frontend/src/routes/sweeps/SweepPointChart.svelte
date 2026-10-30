<!-- The point chart of a sweep of 1 parameter (docs/architecture/backtest.md section 10.11.4): 1 point for each
     parameter value at its metric value. The chart is an SVG with Carbon tokens, not a chart library (section
     10.11.6). The x axis shows each parameter value; the y axis shows the lowest and the highest metric value. -->
<script lang="ts">
  import { formatSweepMetric, type SweepMetricKey, type SweepPoint } from '#lib/sweep';

  interface Props {
    parameter: string;
    points: SweepPoint[];
    metric: SweepMetricKey;
    metricLabel: string;
  }

  const { parameter, points, metric, metricLabel }: Props = $props();

  const WIDTH = 640;
  const HEIGHT = 240;
  const LEFT = 72;
  const RIGHT = 16;
  const TOP = 16;
  const BOTTOM = 40;
  const POINT_RADIUS = 4;
  const LABEL_GAP = 8;
  const HALF = 0.5;
  const TICK_LABEL_OFFSET = 16;

  const values = $derived(points.flatMap((point) => (point.value === null ? [] : [point.value])));
  const lowest = $derived(Math.min(...values));
  const highest = $derived(Math.max(...values));

  function readX(index: number): number {
    const span = WIDTH - LEFT - RIGHT;
    return points.length <= 1 ? LEFT + span * HALF : LEFT + (span * index) / (points.length - 1);
  }

  function readY(value: number): number {
    const span = HEIGHT - TOP - BOTTOM;
    return highest === lowest ? TOP + span * HALF : TOP + (span * (highest - value)) / (highest - lowest);
  }
</script>

<svg class="point-chart" viewBox={`0 0 ${String(WIDTH)} ${String(HEIGHT)}`} role="img" aria-label={`${metricLabel} by ${parameter}`}>
  <line class="axis" x1={LEFT} x2={WIDTH - RIGHT} y1={HEIGHT - BOTTOM} y2={HEIGHT - BOTTOM} />
  {#if values.length > 0}
    <text class="label" x={LEFT - LABEL_GAP} y={readY(highest)} text-anchor="end" dominant-baseline="middle"
      >{formatSweepMetric(metric, highest)}</text
    >
    {#if highest !== lowest}
      <text class="label" x={LEFT - LABEL_GAP} y={readY(lowest)} text-anchor="end" dominant-baseline="middle"
        >{formatSweepMetric(metric, lowest)}</text
      >
    {/if}
  {/if}
  {#each points as point, index (index)}
    <text class="label" x={readX(index)} y={HEIGHT - BOTTOM + TICK_LABEL_OFFSET} text-anchor="middle">{String(point.parameterValue)}</text>
    {#if point.value !== null}
      <circle class="point" cx={readX(index)} cy={readY(point.value)} r={POINT_RADIUS}>
        <title>{parameter} {String(point.parameterValue)}: {formatSweepMetric(metric, point.value)}</title>
      </circle>
    {/if}
  {/each}
  <text class="label" x={(LEFT + WIDTH - RIGHT) * HALF} y={HEIGHT - LABEL_GAP} text-anchor="middle">{parameter}</text>
</svg>

<style>
  .point-chart {
    display: block;
    inline-size: 100%;
    block-size: 100%;
  }

  .axis {
    stroke: var(--cds-border-subtle-01);
  }

  .point {
    fill: var(--cds-support-info);
  }

  .label {
    fill: var(--cds-text-secondary);
    font-family: var(--cds-label-01-font-family, inherit);
    font-size: var(--cds-label-01-font-size);
    font-variant-numeric: tabular-nums;
  }
</style>
