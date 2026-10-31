<!-- A status as an icon alone, for a line that has no space for a word, for example the app header. The icon shape
     and color show the status kind. `label` is the accessible name and the tooltip text: the full status with the
     details. The icon takes the keyboard focus, so the tooltip opens on hover and on focus. -->
<script lang="ts">
  import Icon from './Icon.svelte';
  import { findStatusIcon, type StatusKind } from './status_icon';
  import Tooltip from './Tooltip.svelte';

  interface Props {
    kind: StatusKind;
    label: string;
    /** The side of the tooltip. An icon near the right end of the window uses bottom-end. */
    align?: 'bottom' | 'bottom-start' | 'bottom-end';
  }

  const { kind, label, align = 'bottom' }: Props = $props();
</script>

<Tooltip text={label} {align}>
  {#snippet trigger({ props })}
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <span {...props} class={['status-icon', `status-icon--${kind}`]} role="img" aria-label={label} tabindex="0">
      <Icon icon={findStatusIcon(kind)} />
    </span>
  {/snippet}
</Tooltip>

<style>
  /* A 32px target like a Carbon sm icon button. */
  .status-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    inline-size: var(--cds-spacing-07);
    block-size: var(--cds-spacing-07);
    outline: none;
  }

  .status-icon:focus-visible {
    box-shadow: inset 0 0 0 2px var(--cds-focus);
  }

  .status-icon--success {
    color: var(--cds-support-success);
  }

  .status-icon--in-progress {
    color: var(--cds-support-info);
  }

  .status-icon--warning {
    color: var(--cds-support-warning);
  }

  .status-icon--error {
    color: var(--cds-support-error);
  }

  .status-icon--neutral {
    color: var(--cds-icon-secondary);
  }
</style>
