<!-- A change (up, down, or flat) as text with its sign, an arrow icon, and a Carbon support color. All pages show a
     change with this component, so the color never is the only sign of the direction (AGENTS.md, State). -->
<script lang="ts">
  import ArrowDown16 from '@carbon/icons/es/arrow--down/16.js';
  import ArrowUp16 from '@carbon/icons/es/arrow--up/16.js';
  import { Icon } from '#lib/foundation/carbon';
  import { findChangeDirection } from './value_format';

  interface Props {
    /** The change as a number. Its sign gives the direction. Null is flat. */
    value: number | null;
    /** The change as text, for example from formatSignedNumber. */
    text: string;
    label?: string;
  }

  const { value, text, label }: Props = $props();

  const direction = $derived(findChangeDirection(value));
</script>

<span class={['change', `change--${direction}`]} aria-label={label} data-direction={direction}>
  {#if direction === 'up'}
    <Icon icon={ArrowUp16} />
  {:else if direction === 'down'}
    <Icon icon={ArrowDown16} />
  {/if}
  {text}
</span>

<style>
  .change {
    display: inline-flex;
    align-items: center;
    gap: var(--cds-spacing-02);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    color: var(--cds-text-secondary);
  }

  .change--up {
    color: var(--cds-support-success);
  }

  .change--down {
    color: var(--cds-support-error);
  }

  .change :global(svg) {
    flex: none;
    fill: currentcolor;
  }
</style>
