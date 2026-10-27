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
      {#snippet child({ props })}
        <span {...props} class="cds--popover" role="tooltip">
          <span class="cds--popover-content cds--tooltip-content">{text}</span>
          <span class="cds--popover-caret"></span>
        </span>
      {/snippet}
    </Tooltip.ContentStatic>
  </span>
</Tooltip.Root>
