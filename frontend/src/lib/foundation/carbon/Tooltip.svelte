<!-- Carbon tooltip on Bits UI Tooltip: it opens on hover and on keyboard focus, and Escape closes it.
     The `trigger` snippet renders the trigger element and must spread `props` on it. -->
<script module lang="ts">
  export type TooltipAlignment = 'top' | 'top-start' | 'top-end' | 'bottom' | 'bottom-start' | 'bottom-end' | 'left' | 'right';
</script>

<script lang="ts">
  import { Tooltip } from 'bits-ui';
  import type { Snippet } from 'svelte';

  interface Props {
    text: string;
    align?: TooltipAlignment;
    trigger: Snippet<[{ props: Record<string, unknown> }]>;
  }

  const { text, align = 'bottom', trigger }: Props = $props();

  let open = $state(false);
</script>

<Tooltip.Root bind:open>
  <!-- Carbon shows the popover content only when the container has cds--popover--open. -->
  <span
    class={[
      'cds--popover-container',
      'cds--popover--caret',
      'cds--popover--high-contrast',
      `cds--popover--${align}`,
      'cds--tooltip',
      open && 'cds--popover--open',
    ]}
  >
    <Tooltip.Trigger>
      {#snippet child({ props })}
        {@render trigger({ props })}
      {/snippet}
    </Tooltip.Trigger>
    <Tooltip.ContentStatic>
      <!-- Carbon sizes .cds--popover to the trigger and gives it pointer-events: none. The Bits props set
           pointer-events: auto, so they go on the bubble. On .cds--popover they make the open tooltip take the
           clicks of the trigger. -->
      {#snippet child({ props })}
        <span class="cds--popover">
          <span {...props} class="cds--popover-content cds--tooltip-content" role="tooltip">{text}</span>
          <span class="cds--popover-caret"></span>
        </span>
      {/snippet}
    </Tooltip.ContentStatic>
  </span>
</Tooltip.Root>
