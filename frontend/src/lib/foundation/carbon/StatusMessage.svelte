<!-- A short message that the user must read to act, as a status icon and the text (Carbon status indicator pattern),
     for example the reason that a control is disabled. The icon shape differs for each kind, so the message does not
     depend on the color only. The status of an item is a StatusIndicator (icon alone), not a StatusMessage. -->
<script lang="ts">
  import Icon from './Icon.svelte';
  import { findStatusIcon, type StatusKind } from './status_icon';

  interface Props {
    kind: StatusKind;
    text: string;
  }

  const { kind, text }: Props = $props();
</script>

<span class={['status-message', `status-message--${kind}`]}>
  <Icon icon={findStatusIcon(kind)} class="status-message__icon" />
  <span>{text}</span>
</span>

<style>
  /* vertical-align: top keeps a 32px table row at 32px, like ChangeText. */
  .status-message {
    display: inline-flex;
    align-items: center;
    vertical-align: top;
    gap: var(--cds-spacing-03);
    /* The text breaks only between words, also in a table cell that breaks long values anywhere. */
    overflow-wrap: normal;
  }

  .status-message :global(.status-message__icon) {
    flex: none;
  }

  .status-message--success :global(.status-message__icon) {
    color: var(--cds-support-success);
  }

  .status-message--in-progress :global(.status-message__icon) {
    color: var(--cds-support-info);
  }

  .status-message--warning :global(.status-message__icon) {
    color: var(--cds-support-warning);
  }

  .status-message--error :global(.status-message__icon) {
    color: var(--cds-support-error);
  }

  .status-message--neutral :global(.status-message__icon) {
    color: var(--cds-icon-secondary);
  }
</style>
