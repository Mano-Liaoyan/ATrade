<!-- A status as an icon alone. The icon shape and color show the status kind. `label` is the accessible name and the
     tooltip text: the full status with the details. The icon takes the keyboard focus, so the tooltip opens on hover
     and on focus. `inline` puts the icon in a line of text or a table cell, before the item title. Without it, the
     icon has the 32px box of a Carbon sm icon button, for example in the app header. -->
<script lang="ts">
  import Icon from './Icon.svelte';
  import { findStatusIcon, type StatusKind } from './status_icon';
  import Tooltip from './Tooltip.svelte';

  interface Props {
    kind: StatusKind;
    label: string;
    /** The side of the tooltip. An icon near the right end of the window uses bottom-end. */
    align?: 'top' | 'top-start' | 'top-end' | 'bottom' | 'bottom-start' | 'bottom-end' | 'left' | 'right';
    inline?: boolean;
  }

  const { kind, label, align = 'bottom', inline = false }: Props = $props();
</script>

<Tooltip text={label} {align}>
  {#snippet trigger({ props })}
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <span
      {...props}
      class={['status-icon', `status-icon--${kind}`, inline && 'status-icon--inline']}
      role="img"
      aria-label={label}
      tabindex="0"
    >
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

  /* vertical-align: top keeps a 32px table row at 32px. The gap after the icon separates it from the item title. */
  .status-icon--inline {
    inline-size: auto;
    block-size: auto;
    vertical-align: top;
    margin-inline-end: var(--cds-spacing-03);
  }

  .status-icon:focus-visible {
    box-shadow: inset 0 0 0 2px var(--cds-focus);
  }

  .status-icon--inline:focus-visible {
    box-shadow: 0 0 0 2px var(--cds-focus);
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
