<!-- Carbon tooltip on Bits UI Tooltip: it opens on hover and on keyboard focus, and Escape closes it.
     The `trigger` snippet renders the trigger element and must spread `props` on it.
     Bits UI closes a tooltip when a parent of its trigger scrolls. Keyboard focus on a trigger outside the view of a
     scroll region scrolls that region in the next frame, so the tooltip that the focus opened opens again. -->
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
    trigger: Snippet<[{ props: Record<string, unknown> }]>;
  }

  const { text, align = 'bottom', block = false, trigger }: Props = $props();

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

<style>
  .tooltip--block {
    display: block;
  }
</style>
