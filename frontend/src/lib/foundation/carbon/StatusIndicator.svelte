<!-- The status of an item: the status icon alone, before the item title (UI rule: a status icon stands alone, without a
     word). `label` is the accessible name and the tooltip text, for example "Finished". The icon takes the keyboard
     focus, so the Carbon tooltip opens on hover and on focus. With `iconOnly`, the icon sits inside a control (for
     example a backtest tab): it does not take the focus, and the label is its accessible name and its `title`.
     A text that the user must read to act, for example an error or the reason that a control is disabled, is a
     StatusMessage or an InlineNotification, not a StatusIndicator. -->
<script lang="ts">
  import Icon from './Icon.svelte';
  import StatusIcon from './StatusIcon.svelte';
  import { findStatusIcon, type StatusKind } from './status_icon';

  interface Props {
    kind: StatusKind;
    label: string;
    align?: 'top' | 'top-start' | 'top-end' | 'bottom' | 'bottom-start' | 'bottom-end' | 'left' | 'right';
    /** The icon is inside a control, so it does not take the focus. */
    iconOnly?: boolean;
  }

  const { kind, label, align = 'bottom', iconOnly = false }: Props = $props();
</script>

{#if iconOnly}
  <span class={['status-indicator', `status-indicator--${kind}`]} title={label}>
    <Icon icon={findStatusIcon(kind)} {label} class="status-indicator__icon" />
  </span>
{:else}
  <StatusIcon {kind} {label} {align} inline />
{/if}

<style>
  /* vertical-align: top keeps a 32px row at 32px. */
  .status-indicator {
    display: inline-flex;
    align-items: center;
    vertical-align: top;
  }

  /* The icon keeps its status color also where Carbon fills icons with its own token, for example in a menu item. */
  .status-indicator :global(.status-indicator__icon) {
    flex: none;
    fill: currentColor;
  }

  .status-indicator--success :global(.status-indicator__icon) {
    color: var(--cds-support-success);
  }

  .status-indicator--in-progress :global(.status-indicator__icon) {
    color: var(--cds-support-info);
  }

  .status-indicator--warning :global(.status-indicator__icon) {
    color: var(--cds-support-warning);
  }

  .status-indicator--error :global(.status-indicator__icon) {
    color: var(--cds-support-error);
  }

  .status-indicator--neutral :global(.status-indicator__icon) {
    color: var(--cds-icon-secondary);
  }
</style>
