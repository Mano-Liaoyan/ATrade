<!-- A status as an icon and a word together with its color (Carbon status indicator pattern). The icon shape differs
     for each kind, so the status does not depend on the color only. With `iconOnly`, only the icon shows, in front of a
     name (for example a backtest tab); the word is its accessible name and its tooltip text (`title`). -->
<script module lang="ts">
  export type StatusKind = 'success' | 'in-progress' | 'warning' | 'error' | 'neutral';
</script>

<script lang="ts">
  import CheckmarkFilled16 from '@carbon/icons/es/checkmark--filled/16.js';
  import CircleDash16 from '@carbon/icons/es/circle-dash/16.js';
  import ErrorFilled16 from '@carbon/icons/es/error--filled/16.js';
  import InProgress16 from '@carbon/icons/es/in-progress/16.js';
  import WarningAltFilled16 from '@carbon/icons/es/warning--alt--filled/16.js';
  import type { CarbonIconNode } from './carbon_icon';
  import Icon from './Icon.svelte';

  interface Props {
    kind: StatusKind;
    label: string;
    iconOnly?: boolean;
  }

  const { kind, label, iconOnly = false }: Props = $props();

  function findIcon(statusKind: StatusKind): CarbonIconNode {
    switch (statusKind) {
      case 'success':
        return CheckmarkFilled16;
      case 'in-progress':
        return InProgress16;
      case 'warning':
        return WarningAltFilled16;
      case 'error':
        return ErrorFilled16;
      case 'neutral':
        return CircleDash16;
    }
  }
</script>

{#if iconOnly}
  <span class={['status-indicator', `status-indicator--${kind}`]} title={label}>
    <Icon icon={findIcon(kind)} {label} class="status-indicator__icon" />
  </span>
{:else}
  <span class={['status-indicator', `status-indicator--${kind}`]}>
    <Icon icon={findIcon(kind)} class="status-indicator__icon" />
    <span>{label}</span>
  </span>
{/if}

<style>
  /* vertical-align: top keeps a 32px table row at 32px, like ChangeText. */
  .status-indicator {
    display: inline-flex;
    align-items: center;
    vertical-align: top;
    gap: var(--cds-spacing-03);
    /* The status word breaks only between words, also in a table cell that breaks long values anywhere. */
    overflow-wrap: normal;
  }

  .status-indicator :global(.status-indicator__icon) {
    flex: none;
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
