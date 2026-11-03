<!-- Carbon tooltip on Bits UI Tooltip: it opens on hover and on keyboard focus, and Escape closes it.
     The `trigger` snippet renders the trigger element and must spread `props` on it.
     Bits UI closes a tooltip when a parent of its trigger scrolls. Keyboard focus on a trigger outside the view of a
     scroll region scrolls that region in the next frame, so the tooltip that the focus opened opens again.
     With `floating`, the tooltip goes under <body> (no caret), so a scroll region cannot clip it, for example in a chart
     legend. -->
<script module lang="ts">
  export type TooltipAlignment = 'top' | 'top-start' | 'top-end' | 'bottom' | 'bottom-start' | 'bottom-end' | 'left' | 'right';
</script>

<script lang="ts">
  import { Tooltip } from 'bits-ui';
  import type { Snippet } from 'svelte';

  interface Props {
    text: string;
    align?: TooltipAlignment;
    /** The trigger is a block, for example a notification: the tooltip container takes the full width. */
    block?: boolean;
    /** The tooltip goes under <body>, out of a parent that clips it. */
    floating?: boolean;
    trigger: Snippet<[{ props: Record<string, unknown> }]>;
  }

  const { text, align = 'bottom', block = false, floating = false, trigger }: Props = $props();

  // The side and the alignment of a floating tooltip, from the Carbon alignment.
  const floatingSide = $derived(align.split('-')[0] as 'top' | 'bottom' | 'left' | 'right');
  const floatingAlign = $derived(align.endsWith('-start') ? 'start' : align.endsWith('-end') ? 'end' : 'center');
  // $spacing-02 between the trigger and the floating tooltip.
  const FLOATING_GAP_PIXELS = 4;

  let open = $state(false);

  // The scroll event of a focus comes before the animation frame callbacks of the next frame. Two frames are safe.
  const FRAMES_AFTER_FOCUS = 2;

  function keepOpenAfterFocusScroll(triggerElement: EventTarget | null, framesLeft: number): void {
    requestAnimationFrame(() => {
      if (framesLeft > 1) {
        keepOpenAfterFocusScroll(triggerElement, framesLeft - 1);
      } else if (document.activeElement === triggerElement) {
        open = true;
      }
    });
  }

  function withFocusScrollFix(props: Record<string, unknown>): Record<string, unknown> {
    const bitsFocusHandler = props['onfocus'] as ((event: FocusEvent) => void) | undefined;
    return {
      ...props,
      onfocus: (event: FocusEvent) => {
        bitsFocusHandler?.(event);
        // Only a tooltip that the focus opened opens again. A pointer focus does not open it.
        if (open) {
          keepOpenAfterFocusScroll(event.currentTarget, FRAMES_AFTER_FOCUS);
        }
      },
    };
  }
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
      block && 'tooltip--block',
    ]}
  >
    <Tooltip.Trigger>
      {#snippet child({ props })}
        {@render trigger({ props: withFocusScrollFix(props) })}
      {/snippet}
    </Tooltip.Trigger>
    {#if floating}
      <Tooltip.Portal>
        <Tooltip.Content side={floatingSide} align={floatingAlign} sideOffset={FLOATING_GAP_PIXELS}>
          {#snippet child({ wrapperProps, props, open: isOpen })}
            {#if isOpen}
              <div {...wrapperProps}>
                <span class="cds--popover-container cds--popover--high-contrast cds--popover--open cds--tooltip floating-tooltip">
                  <span class="cds--popover">
                    <span {...props} class="cds--popover-content cds--tooltip-content" role="tooltip">{text}</span>
                  </span>
                </span>
              </div>
            {/if}
          {/snippet}
        </Tooltip.Content>
      </Tooltip.Portal>
    {:else}
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
    {/if}
  </span>
</Tooltip.Root>

<style>
  /* Bits UI places the floating wrapper, so the Carbon offsets of the popover and its content go. */
  .floating-tooltip,
  .floating-tooltip .cds--popover,
  .floating-tooltip .cds--popover-content {
    position: relative;
    inset: auto;
    transform: none;
  }

  .tooltip--block {
    display: block;
  }
</style>
