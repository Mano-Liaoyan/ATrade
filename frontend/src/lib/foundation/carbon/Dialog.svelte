<!-- Carbon modal on Bits UI Dialog. Focus stays in the dialog while it is open, Escape and a click outside close it,
     and focus goes back to `returnFocus` (or to the element that had focus before) when it closes. The footer has
     the secondary button and the primary button side by side. The title is the accessible name of the dialog.
     Without `primaryText`, the dialog is a Carbon passive modal: no footer, the content has its own controls (for
     example a form with its own submit button), and the Close button closes it. -->
<script lang="ts">
  import Close20 from '@carbon/icons/es/close/20.js';
  import { Dialog } from 'bits-ui';
  import type { Snippet } from 'svelte';
  import Icon from './Icon.svelte';
  import { buttonClasses, type ButtonKind } from './carbon_state';

  interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    title: string;
    // The small text above the title. Give it only when the user needs it to act.
    label?: string;
    primaryText?: string;
    primaryKind?: ButtonKind;
    secondaryText?: string;
    // True while the primary action runs: the buttons do not react.
    busy?: boolean;
    size?: 'xs' | 'sm' | 'md' | 'lg';
    // The element that gets focus when the dialog closes, for example the button that opened the dialog from code.
    returnFocus?: HTMLElement | null;
    onPrimary?: () => void;
    children: Snippet;
  }

  const {
    open,
    onOpenChange,
    title,
    label,
    primaryText,
    primaryKind = 'primary',
    secondaryText = 'Cancel',
    busy = false,
    size = 'sm',
    returnFocus = null,
    onPrimary,
    children,
  }: Props = $props();

  // The modal title is an h2: the dialog is outside the page outline, and the page has its own h1.
  const TITLE_LEVEL = 2;

  function focusReturnElement(event: Event): void {
    if (returnFocus !== null) {
      event.preventDefault();
      returnFocus.focus();
    }
  }
</script>

<Dialog.Root {open} {onOpenChange}>
  <Dialog.Portal>
    <!-- The Carbon modal element is the backdrop. Bits UI renders the Portal children also when the dialog is closed,
         so the backdrop is rendered only while the dialog is open. -->
    {#if open}
      <div class="cds--modal is-visible">
        <Dialog.Content
          onCloseAutoFocus={focusReturnElement}
          escapeKeydownBehavior={busy ? 'ignore' : 'close'}
          interactOutsideBehavior={busy ? 'ignore' : 'close'}
        >
          {#snippet child({ props })}
            <div {...props} class={['cds--modal-container', size !== 'md' && `cds--modal-container--${size}`]}>
              <div class="cds--modal-header">
                {#if label !== undefined}
                  <p class="cds--modal-header__label">{label}</p>
                {/if}
                <Dialog.Title level={TITLE_LEVEL}>
                  {#snippet child({ props: titleProps })}
                    <h2 {...titleProps} class="cds--modal-header__heading">{title}</h2>
                  {/snippet}
                </Dialog.Title>
                <div class="cds--modal-close-button">
                  <Dialog.Close>
                    {#snippet child({ props: closeProps })}
                      <button
                        {...closeProps}
                        type="button"
                        class={['cds--modal-close', ...buttonClasses({ kind: 'ghost', size: 'lg', iconOnly: true })]}
                        aria-label="Close"
                        disabled={busy}
                      >
                        <Icon icon={Close20} class="cds--modal-close__icon" />
                      </button>
                    {/snippet}
                  </Dialog.Close>
                </div>
              </div>
              <div class="cds--modal-content">
                {@render children()}
              </div>
              {#if primaryText !== undefined}
              <div class="cds--modal-footer cds--btn-set">
                <Dialog.Close>
                  {#snippet child({ props: cancelProps })}
                    <button {...cancelProps} type="button" class={buttonClasses({ kind: 'secondary', size: 'lg' })} disabled={busy}>
                      {secondaryText}
                    </button>
                  {/snippet}
                </Dialog.Close>
                <button type="button" class={buttonClasses({ kind: primaryKind, size: 'lg' })} disabled={busy} onclick={onPrimary}>
                  {primaryText}
                </button>
              </div>
              {/if}
            </div>
          {/snippet}
        </Dialog.Content>
      </div>
    {/if}
  </Dialog.Portal>
</Dialog.Root>
