<!-- Carbon popover (drop shadow, no caret) on Bits UI Popover. It opens below `anchor`, an element that the caller
     gives, so one popover can serve many triggers (for example the tags of a condition bar). Escape and a click
     outside close it, and focus goes back to the anchor. The popover goes under <body>, so a scroll region cannot
     clip it. `label` is the accessible name of the popover dialog. -->
<script lang="ts">
  import { Popover } from 'bits-ui';
  import type { Snippet } from 'svelte';

  interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    anchor: HTMLElement | null;
    label: string;
    children: Snippet;
  }

  const { open, onOpenChange, anchor, label, children }: Props = $props();

  // $spacing-02 between the anchor and the popover; $spacing-05 from the window edges.
  const ANCHOR_GAP_PIXELS = 4;
  const WINDOW_PADDING_PIXELS = 16;

  function focusAnchor(event: Event): void {
    if (anchor?.isConnected === true) {
      event.preventDefault();
      anchor.focus();
    }
  }
</script>

<Popover.Root {open} {onOpenChange}>
  <Popover.Portal>
    <Popover.Content
      customAnchor={anchor}
      side="bottom"
      align="start"
      sideOffset={ANCHOR_GAP_PIXELS}
      collisionPadding={WINDOW_PADDING_PIXELS}
      onCloseAutoFocus={focusAnchor}
    >
      {#snippet child({ wrapperProps, props, open: isOpen })}
        {#if isOpen}
          <div {...wrapperProps}>
            <div class="cds--popover-container cds--popover--drop-shadow cds--popover--open floating-popover">
              <div class="cds--popover">
                <div {...props} class="cds--popover-content popover-content" role="dialog" aria-label={label}>
                  {@render children()}
                </div>
              </div>
            </div>
          </div>
        {/if}
      {/snippet}
    </Popover.Content>
  </Popover.Portal>
</Popover.Root>

<style>
  /* Carbon places the popover with absolute offsets from its trigger. Bits UI places the floating wrapper, so the
     popover and its content stay in the flow of the wrapper. */
  .floating-popover,
  .floating-popover .cds--popover,
  .popover-content {
    position: relative;
    inset: auto;
  }

  .popover-content {
    inline-size: 20rem;
  }
</style>
