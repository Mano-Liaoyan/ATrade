<!-- A status as an icon and a word together with its color (Carbon status indicator pattern). The icon shape differs
     for each kind, so the status does not depend on the color only. -->
<script lang="ts">
  import Icon from './Icon.svelte';
  import { findStatusIcon, type StatusKind } from './status_icon';

  interface Props {
    kind: StatusKind;
    label: string;
  }

  const { kind, label }: Props = $props();
</script>

<span class={['status-indicator', `status-indicator--${kind}`]}>
  <Icon icon={findStatusIcon(kind)} class="status-indicator__icon" />
  <span>{label}</span>
</span>

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
