<!-- Carbon inline notification. It shows a result with an icon and a color: success and info are a status, error and
     warning are an alert. With onClose, it has a close button. -->
<script lang="ts">
  import CheckmarkFilled20 from '@carbon/icons/es/checkmark--filled/20.js';
  import Close20 from '@carbon/icons/es/close/20.js';
  import ErrorFilled20 from '@carbon/icons/es/error--filled/20.js';
  import InformationFilled20 from '@carbon/icons/es/information--filled/20.js';
  import WarningFilled20 from '@carbon/icons/es/warning--filled/20.js';
  import type { Snippet } from 'svelte';
  import type { CarbonIconNode } from './carbon_icon';
  import Icon from './Icon.svelte';
  import type { NotificationKind } from './notification_message';

  interface Props {
    kind: NotificationKind;
    title: string;
    subtitle?: string;
    lowContrast?: boolean;
    onClose?: () => void;
    // More content below the subtitle, for example a list of problems.
    children?: Snippet;
    // The accessible name of the status or alert, when the page names it.
    label?: string;
  }

  const { kind, title, subtitle, lowContrast = false, onClose, children, label }: Props = $props();

  function findIcon(notificationKind: NotificationKind): CarbonIconNode {
    switch (notificationKind) {
      case 'success':
        return CheckmarkFilled20;
      case 'error':
        return ErrorFilled20;
      case 'info':
        return InformationFilled20;
      case 'warning':
        return WarningFilled20;
    }
  }
</script>

<div
  class={[
    'cds--inline-notification',
    `cds--inline-notification--${kind}`,
    lowContrast && 'cds--inline-notification--low-contrast',
    onClose === undefined && 'cds--inline-notification--hide-close-button',
  ]}
  role={kind === 'error' || kind === 'warning' ? 'alert' : 'status'}
  aria-label={label}
>
  <div class="cds--inline-notification__details">
    <Icon icon={findIcon(kind)} class="cds--inline-notification__icon" />
    <div class="cds--inline-notification__text-wrapper">
      <div class="cds--inline-notification__title">{title}</div>
      {#if subtitle !== undefined}
        <div class="cds--inline-notification__subtitle">{subtitle}</div>
      {/if}
      {#if children !== undefined}
        <div class="cds--inline-notification__subtitle">{@render children()}</div>
      {/if}
    </div>
  </div>
  {#if onClose !== undefined}
    <button class="cds--inline-notification__close-button" type="button" aria-label="Close notification" onclick={onClose}>
      <Icon icon={Close20} class="cds--inline-notification__close-icon" />
    </button>
  {/if}
</div>
