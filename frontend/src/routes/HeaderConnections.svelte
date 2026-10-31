<!-- The Connections button of the app shell header: a Carbon header action with the plug icon. When the backend and
     IB Gateway are connected, the icon has no badge. A problem adds a Carbon status icon as a badge on the icon corner.
     The badge shape differs for each status kind. The button name and the tooltip name the problem. A click, Enter, or
     Space opens a Carbon popover with one row for the backend (with the server time) and one row for IB Gateway. -->
<script lang="ts">
  import CheckmarkFilled16 from '@carbon/icons/es/checkmark--filled/16.js';
  import ErrorFilled16 from '@carbon/icons/es/error--filled/16.js';
  import InProgress16 from '@carbon/icons/es/in-progress/16.js';
  import Plug20 from '@carbon/icons/es/plug/20.js';
  import WarningAltFilled16 from '@carbon/icons/es/warning--alt--filled/16.js';
  import { Icon, Popover, Tooltip, type CarbonIcon, type StatusKind } from '#lib/foundation/carbon';
  import type { HeaderConnections } from './header_connections';

  const { connections }: { connections: HeaderConnections } = $props();

  const STATUS_ICONS: Record<StatusKind, CarbonIcon> = {
    success: CheckmarkFilled16,
    'in-progress': InProgress16,
    warning: WarningAltFilled16,
    error: ErrorFilled16,
    neutral: InProgress16,
  };

  let open = $state(false);
  let button: HTMLElement | null = $state(null);
</script>

<Tooltip text={connections.label} align="bottom-end">
  {#snippet trigger({ props })}
    <button
      {...props}
      bind:this={button}
      type="button"
      class={['cds--header__action', 'cds--btn--icon-only', open && 'cds--header__action--active']}
      aria-label={connections.label}
      aria-haspopup="dialog"
      aria-expanded={open}
      onclick={() => {
        open = true;
      }}
    >
      <span class="connections-icon">
        <Icon icon={Plug20} />
        {#if connections.badge !== null}
          <span class={['connections-badge', `connections-status--${connections.badge}`]}>
            <Icon icon={STATUS_ICONS[connections.badge]} />
          </span>
        {/if}
      </span>
    </button>
  {/snippet}
</Tooltip>

<Popover
  {open}
  onOpenChange={(isOpen: boolean) => {
    open = isOpen;
  }}
  anchor={button}
  label="Connections"
>
  <ul class="connections-list">
    {#each connections.rows as row (row.name)}
      <li class="connections-row">
        <span class={['connections-row__status', `connections-status--${row.kind}`]}>
          <Icon icon={STATUS_ICONS[row.kind]} label={row.stateLabel} />
        </span>
        <span class="connections-row__name">{row.name}</span>
        {#if row.serverTime !== null}
          <span class="connections-row__detail" role="timer" aria-label="Server time">Server time {row.serverTime}</span>
        {/if}
        {#if row.detail !== null}
          <span class="connections-row__detail">{row.detail}</span>
        {/if}
      </li>
    {/each}
  </ul>
</Popover>

<style>
  .connections-icon {
    position: relative;
    display: inline-flex;
  }

  /* The badge is a 12px Carbon status icon on the top end corner of the 20px icon. A ring in the header background
     cuts it out of the plug. */
  .connections-badge {
    position: absolute;
    inset-block-start: calc(-1 * var(--cds-spacing-02));
    inset-inline-end: calc(-1 * var(--cds-spacing-03));
    display: inline-flex;
    padding: 1px;
    border-radius: 50%;
    background: var(--cds-background);
  }

  .connections-badge :global(svg) {
    inline-size: var(--cds-spacing-04);
    block-size: var(--cds-spacing-04);
  }

  .connections-list {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .connections-row {
    display: grid;
    grid-template-columns: var(--cds-spacing-05) 1fr;
    column-gap: var(--cds-spacing-03);
    row-gap: var(--cds-spacing-01);
    padding: var(--cds-spacing-04) var(--cds-spacing-05);
  }

  .connections-row + .connections-row {
    border-block-start: 1px solid var(--cds-border-subtle-01);
  }

  .connections-row__status {
    display: inline-flex;
    align-items: center;
  }

  .connections-row__name {
    font-size: var(--cds-body-compact-01-font-size);
    font-weight: var(--cds-body-compact-01-font-weight);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
    color: var(--cds-text-primary);
  }

  .connections-row__detail {
    grid-column: 2;
    font-size: var(--cds-helper-text-01-font-size);
    line-height: var(--cds-helper-text-01-line-height);
    letter-spacing: var(--cds-helper-text-01-letter-spacing);
    color: var(--cds-text-secondary);
    font-variant-numeric: tabular-nums;
  }

  .connections-status--success {
    color: var(--cds-support-success);
  }

  .connections-status--in-progress {
    color: var(--cds-support-info);
  }

  .connections-status--warning {
    color: var(--cds-support-warning);
  }

  .connections-status--error {
    color: var(--cds-support-error);
  }
</style>
